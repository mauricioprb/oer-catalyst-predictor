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

        surface_energy, _ = self._compute_surface_energy(
            structure, bulk_pred["e_per_atom"]
        )

        dg_oh, dg_o, dg_ooh = self._compute_oer_energies(
            structure, bulk_pred, surface_energy
        )

        overpotential = self._compute_overpotential(dg_oh, dg_o, dg_ooh)
        band_gap = self._estimate_band_gap(structure, bulk_pred)

        is_viable = overpotential < LIMIAR_OVERPOTENTIAL
        formula = structure.composition.reduced_formula

        logger.info(
            "CHGNet: %s | η=%.4f V | viável=%s | e=%.4f eV/at | γ=%.3f J/m²",
            formula, overpotential, is_viable,
            bulk_pred["e_per_atom"], surface_energy,
        )

        return OERResult(
            formula=formula,
            band_gap_eV=round(band_gap, 4),
            overpotential_V=round(overpotential, 4),
            is_viable=is_viable,
            delta_G_O=round(dg_o, 4),
            delta_G_OH=round(dg_oh, 4),
            delta_G_OOH=round(dg_ooh, 4),
        )

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

    def _compute_surface_energy(
        self, structure: Structure, e_bulk: float
    ) -> tuple[float, float]:
        from ase.constraints import FixAtoms
        from ase.optimize import BFGS

        slab = self._find_best_slab(structure)
        if slab is None:
            logger.warning("Sem slab válido. Usando γ=0.75 J/m².")
            return 0.75, e_bulk

        atoms = self._adaptor.get_atoms(slab)
        z = atoms.positions[:, 2]
        z_mid = (z.max() + z.min()) / 2.0
        atoms.set_constraint(FixAtoms(mask=z < z_mid))
        atoms.calc = self._make_calculator()

        try:
            BFGS(atoms, logfile=None).run(fmax=0.05, steps=80)
        except Exception as exc:
            logger.warning("Relaxação slab falhou: %s", exc)

        E_slab = atoms.get_potential_energy()
        n_slab = len(atoms)
        e_slab = E_slab / n_slab

        area = float(np.linalg.norm(
            np.cross(slab.lattice.matrix[0], slab.lattice.matrix[1])
        ))
        area = max(area, 1.0)

        gamma = (E_slab - n_slab * e_bulk) / (2.0 * area) * 16.0218
        gamma = max(gamma, 0.0)

        logger.debug("Slab: %d at, γ=%.3f J/m²", n_slab, gamma)
        return float(gamma), e_slab

    def _find_best_slab(self, structure: Structure):
        for hkl in MILLER_INDICES:
            try:
                slabs = SlabGenerator(
                    structure, list(hkl),
                    min_slab_size=8.0, min_vacuum_size=15.0,
                    center_slab=True,
                ).get_slabs()
                sym = [s for s in slabs if s.is_symmetric()]
                if sym:
                    return sym[0]
                non_polar = [s for s in slabs if not s.is_polar()]
                if non_polar:
                    return non_polar[0]
            except Exception:
                continue

        try:
            slabs = SlabGenerator(
                structure, [1, 1, 0],
                min_slab_size=6.0, min_vacuum_size=12.0,
                center_slab=True,
            ).get_slabs()
            return slabs[0] if slabs else None
        except Exception:
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
        symbols = {str(sp) for sp in structure.species}
        metals = symbols & METAIS_TRANSICAO
        if not metals:
            return "Ru"
        dg_vals = [(m, METAL_DG_OH.get(m, DEFAULT_DG_OH)) for m in metals]
        best, _ = min(dg_vals, key=lambda x: abs(x[1] - 1.60))
        return best

    @staticmethod
    def _get_baseline_dg_oh(structure: Structure) -> float:
        symbols = {str(sp) for sp in structure.species}
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
        cif_error = None
        xyz_error = None

        try:
            structure = Structure.from_str(file_content, fmt="cif")
            logger.debug("CIF parsed: %s", structure.formula)
            return structure
        except Exception as exc:
            cif_error = exc

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xyz", delete=False
            ) as tmp:
                tmp.write(file_content)
                tmp_path = Path(tmp.name)
            structure = Structure.from_file(str(tmp_path), fmt="xyz")
            logger.debug("XYZ parsed: %s", structure.formula)
            return structure
        except Exception as exc:
            xyz_error = exc
        finally:
            if tmp_path:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        raise CIFParsingError(
            f"CIF error: {cif_error}  |  XYZ error: {xyz_error}"
        )

    @staticmethod
    def _validate_composition(structure: Structure) -> None:
        symbols = {str(sp) for sp in structure.species}
        if "O" not in symbols:
            raise InvalidCatalystError(
                f"{structure.composition.reduced_formula} não contém O."
            )
        if not (symbols & METAIS_TRANSICAO):
            raise InvalidCatalystError(
                f"{structure.composition.reduced_formula} sem metal de transição. "
                f"Encontrados: {sorted(symbols)}."
            )
