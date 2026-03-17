from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TypedDict

import numpy as np
import torch
from pymatgen.core import Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.ase import AseAtomsAdaptor

from app.domain.constants import (
    DEFAULT_DG_OH,
    E_OER_REVERSIVEL,
    LIMIAR_OVERPOTENTIAL,
    METAIS_TRANSICAO,
    METAL_DG_OH,
    MILLER_INDICES,
    SURFACE_ENERGY_REFS,
)
from app.domain.exceptions import CIFParsingError, InvalidCatalystError

logger: logging.Logger = logging.getLogger(__name__)


class OERResult(TypedDict):
    formula: str
    band_gap_eV: float
    overpotential_V: float
    is_viable: bool
    delta_G_O: float
    delta_G_OH: float
    delta_G_OOH: float


class OERPredictor:

    def __init__(self, *, device: str | None = None) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            from chgnet.model import CHGNet
            from chgnet.model.dynamics import CHGNetCalculator

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device_str = device
        self._model: CHGNet = CHGNet.load(use_device=device)
        self._CHGNetCalculator = CHGNetCalculator
        self._adaptor = AseAtomsAdaptor()

        n_params = sum(p.numel() for p in self._model.parameters())
        logger.info(
            "CHGNet carregado em %s (%d parâmetros)", device, n_params
        )

    def _make_calculator(self):
        return self._CHGNetCalculator(model=self._model)

    def predict_oer_activity(self, file_content: str) -> OERResult:
        structure = self._parse_structure(file_content)
        self._validate_composition(structure)

        bulk_pred = self._predict_bulk(structure)
        e_bulk = bulk_pred["e_per_atom"]
        
        results: list[OERResult] = []

        for hkl in MILLER_INDICES:
            try:
                slab = self._generate_slab(structure, hkl)
                if slab is None:
                    continue

                surface_energy, _ = self._compute_surface_energy_for_slab(
                    slab, e_bulk
                )

                dg_oh, dg_o, dg_ooh = self._compute_oer_energies(
                    structure, bulk_pred, surface_energy
                )

                overpotential = self._compute_overpotential(dg_oh, dg_o, dg_ooh)
                band_gap = self._estimate_band_gap(structure, bulk_pred)

                is_viable = overpotential < LIMIAR_OVERPOTENTIAL
                formula = structure.composition.reduced_formula

                results.append(OERResult(
                    formula=f"{formula} ({hkl[0]}{hkl[1]}{hkl[2]})",
                    band_gap_eV=round(band_gap, 4),
                    overpotential_V=round(overpotential, 4),
                    is_viable=is_viable,
                    delta_G_O=round(dg_o, 4),
                    delta_G_OH=round(dg_oh, 4),
                    delta_G_OOH=round(dg_ooh, 4),
                ))
                
                logger.info(
                    "Faceta %s: η=%.4f V | γ=%.3f J/m²",
                    hkl, overpotential, surface_energy
                )

            except Exception as exc:
                logger.warning("Falha ao analisar faceta %s: %s", hkl, exc)
                continue

        if not results:
            raise InvalidCatalystError("Não foi possível gerar ou relaxar nenhum slab para as facetas principais.")

        best_result = min(results, key=lambda x: x["overpotential_V"])
        
        logger.info(
            "Melhor resultado: %s | η=%.4f V | viável=%s",
            best_result["formula"], best_result["overpotential_V"], best_result["is_viable"]
        )

        return best_result

    def _predict_bulk(self, structure: Structure) -> dict:
        pred = self._model.predict_structure(structure)

        e_per_atom = float(pred["e"])
        n = len(structure)
        forces = np.array(pred["f"]) if pred.get("f") is not None else np.zeros((n, 3))
        stress = np.array(pred["s"]) if pred.get("s") is not None else np.zeros((3, 3))
        magmoms = np.array(pred["m"]) if pred.get("m") is not None else np.zeros(n)

        metal_mags = []
        for i, sp in enumerate(structure.species):
            if str(sp) in METAIS_TRANSICAO:
                metal_mags.append(abs(float(magmoms[i])))
        avg_mag = float(np.mean(metal_mags)) if metal_mags else 0.0

        logger.debug(
            "CHGNet bulk: e=%.4f eV/at, μ_metal=%.3f μ_B",
            e_per_atom, avg_mag,
        )

        return {
            "e_per_atom": e_per_atom,
            "total_energy": e_per_atom * n,
            "forces": forces,
            "stress": stress,
            "magmoms": magmoms,
            "metal_avg_magmom": avg_mag,
        }

    def _compute_surface_energy_for_slab(
        self, slab, e_bulk: float
    ) -> tuple[float, float]:
        from ase.constraints import FixAtoms
        from ase.optimize import BFGS

        atoms = self._adaptor.get_atoms(slab)
        z = atoms.positions[:, 2]
        z_mid = (z.max() + z.min()) / 2.0
        atoms.set_constraint(FixAtoms(mask=z < z_mid))
        atoms.calc = self._make_calculator()

        try:
            BFGS(atoms, logfile=None).run(fmax=0.08, steps=50)
        except Exception as exc:
            logger.warning("Relaxação slab instável: %s", exc)

        E_slab = atoms.get_potential_energy()
        n_slab = len(atoms)
        e_slab = E_slab / n_slab

        area = float(np.linalg.norm(
            np.cross(slab.lattice.matrix[0], slab.lattice.matrix[1])
        ))
        area = max(area, 0.1)

        gamma = (E_slab - n_slab * e_bulk) / (2.0 * area) * 16.0218
        gamma = max(gamma, 0.0)

        return float(gamma), e_slab

    def _generate_slab(self, structure: Structure, hkl: tuple[int, int, int]):
        """Gera um slab simétrico para um dado índice de Miller."""
        try:
            gen = SlabGenerator(
                structure, list(hkl),
                min_slab_size=7.5, min_vacuum_size=12.0,
                center_slab=True,
            )
            slabs = gen.get_slabs()
            if not slabs:
                return None
                
            sym = [s for s in slabs if s.is_symmetric()]
            if sym:
                return sym[0]
            
            non_polar = [s for s in slabs if not s.is_polar()]
            return non_polar[0] if non_polar else slabs[0]
        except Exception as e:
            logger.debug("Falha ao gerar slab %s: %s", hkl, e)
            return None


    def _compute_oer_energies(
        self, structure: Structure, bulk_pred: dict, surface_energy: float
    ) -> tuple[float, float, float]:
        baseline = self._get_baseline_dg_oh(structure)
        metal = self._get_principal_metal(structure)

        gamma_ref = SURFACE_ENERGY_REFS.get(metal, 0.75)
        d_gamma = surface_energy - gamma_ref
        corr_gamma = -0.15 * d_gamma

        corr_bulk = 0.0

        magmom = bulk_pred["metal_avg_magmom"]
        corr_mag = 0.02 * (magmom - 1.0)

        total_corr = float(np.clip(
            corr_gamma + corr_bulk + corr_mag, -0.30, 0.30
        ))

        dg_oh = baseline + total_corr
        dg_o = 2.0 * dg_oh
        dg_ooh = dg_oh + 3.20

        logger.debug(
            "ΔG_OH=%.4f (base=%.2f, Δγ=%.4f, Δμ=%.4f, total=%.4f)",
            dg_oh, baseline, corr_gamma, corr_mag, total_corr,
        )
        return dg_oh, dg_o, dg_ooh

    @staticmethod
    def _get_principal_metal(structure: Structure) -> str:
        symbols = {getattr(sp, "symbol", str(sp)) for sp in structure.species}
        metals = symbols & METAIS_TRANSICAO
        if not metals:
            return "Ru"
        dg_vals = [(m, METAL_DG_OH.get(m, DEFAULT_DG_OH)) for m in metals]
        best, _ = min(dg_vals, key=lambda x: abs(x[1] - 1.60))
        return best

    @staticmethod
    def _get_baseline_dg_oh(structure: Structure) -> float:
        symbols = {getattr(sp, "symbol", str(sp)) for sp in structure.species}
        metals = symbols & METAIS_TRANSICAO
        if not metals:
            return DEFAULT_DG_OH
        dg_vals = [(m, METAL_DG_OH.get(m, DEFAULT_DG_OH)) for m in metals]
        _, best_dg = min(dg_vals, key=lambda x: abs(x[1] - 1.60))
        return best_dg

    @staticmethod
    def _compute_overpotential(dg_oh: float, dg_o: float, dg_ooh: float) -> float:
        e_total = 4.0 * E_OER_REVERSIVEL
        dg1 = dg_oh
        dg2 = dg_o - dg_oh
        dg3 = dg_ooh - dg_o
        dg4 = e_total - dg_ooh
        return max(max(dg1, dg2, dg3, dg4) - E_OER_REVERSIVEL, 0.0)

    def _estimate_band_gap(self, structure: Structure, bulk_pred: dict) -> float:
        magmom = bulk_pred["metal_avg_magmom"]
        e_bulk = bulk_pred["e_per_atom"]
        symbols = {str(sp) for sp in structure.species}
        metals = symbols & METAIS_TRANSICAO
        d0 = {"Sc", "Ti", "Zr", "Hf", "Y", "La", "Ta", "Nb", "V"}

        if metals and metals.issubset(d0):
            gap = 3.0 + 0.3 * (abs(e_bulk) - 7.0)
            return float(np.clip(gap, 2.5, 5.0))
        if magmom > 2.0:
            gap = 1.5 + 0.3 * magmom
            return float(np.clip(gap, 1.5, 4.5))
        if magmom < 0.5:
            gap = 0.1 + 0.15 * magmom
            return float(np.clip(gap, 0.0, 1.0))
        gap = 1.0 + 0.5 * magmom
        return float(np.clip(gap, 0.5, 3.0))

    @staticmethod
    def _parse_structure(file_content: str) -> Structure:
        content = file_content.strip()
        if not content:
            raise CIFParsingError("Conteúdo do arquivo está vazio (após strip).")

        from pymatgen.io.cif import CifParser
        from io import StringIO
        
        try:
            parser = CifParser(StringIO(content))
            structures = parser.get_structures(primitive=False)
            if structures:
                logger.debug("CIF parsed via CifParser: %s", structures[0].formula)
                return structures[0]
        except Exception as exc:
            logger.warning("Falha inicial no CifParser: %s", exc)

        for fmt in ["cif", "poscar", "vasp", "xyz"]:
            try:
                structure = Structure.from_str(content, fmt=fmt)
                logger.debug("Estrutura lida via from_str (fmt=%s): %s", fmt, structure.formula)
                return structure
            except Exception:
                continue

        try:
            import tempfile
            from ase.io import read
            from pymatgen.io.ase import AseAtomsAdaptor
            
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
                
            try:
                atoms = read(tmp_path)
                structure = AseAtomsAdaptor.get_structure(atoms)
                logger.debug("Estrutura lida via ASE fallback: %s", structure.formula)
                return structure
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as ase_exc:
            logger.error("Fallback ASE também falhou: %s", ase_exc)

        raise CIFParsingError(
            "Não foi possível identificar uma estrutura cristalina válida no arquivo. "
            "Certifique-se de que o arquivo .cif ou .xyz está no formato correto."
        )

    @staticmethod
    def _validate_composition(structure: Structure) -> None:
        symbols = {getattr(sp, "symbol", str(sp)) for sp in structure.species}
        
        if "O" not in symbols:
            raise InvalidCatalystError(
                f"{structure.composition.reduced_formula} não contém oxigênio (O)."
            )
            
        metais_no_catalisador = symbols & METAIS_TRANSICAO
        if not metais_no_catalisador:
            raise InvalidCatalystError(
                f"{structure.composition.reduced_formula} não possui metais de transição conhecidos. "
                f"Encontrados: {', '.join(sorted(symbols))}."
            )
