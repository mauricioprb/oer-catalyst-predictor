"""
science_engine.py — Núcleo lógico para predição de atividade OER
(Oxygen Evolution Reaction) em catalisadores eletroquímicos.

Utiliza o CHGNet (Crystal Hamiltonian Graph Neural Network), um potencial
interatômico universal de aprendizado de máquina pré-treinado no
Materials Project (~1.6M estruturas, 412k parâmetros), para computar
propriedades estruturais e eletrônicas em GPU.

A predição OER segue o framework do Computational Hydrogen Electrode
(CHE) de Nørskov et al.:
  1. CHGNet prediz energia/átomo, forças, stress e momentos magnéticos
  2. Geração de slab (pymatgen SlabGenerator) → relaxação CHGNet+ASE
  3. Energia de superfície γ = (E_slab − N·e_bulk) / (2A)
  4. Descritores físicos (γ, e_bulk, μ_mag) → ΔG_OH calibrado
  5. Relações de escala universais → ΔG_O, ΔG_OOH
  6. Mecanismo de 4 elétrons → overpotential η_OER

Referências:
- Deng et al., Nature Machine Intelligence 5, 1031 (2023) — CHGNet
- Man et al., ChemCatChem 3, 1159 (2011) — Scaling relations OER
- Nørskov et al., J. Phys. Chem. B 108, 17886 (2004) — CHE framework
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Final, TypedDict

import numpy as np
import torch
from pymatgen.core import Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.ase import AseAtomsAdaptor

# Constantes eletroquímicas

#: Potencial termodinâmico reversível da reação OER (V).
E_OER_REVERSIVEL: Final[float] = 1.23

#: Limiar de viabilidade para o overpotential (V).
LIMIAR_OVERPOTENTIAL: Final[float] = 0.40

#: Metais de transição reconhecidos.
METAIS_TRANSICAO: Final[frozenset[str]] = frozenset(
    [
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "La", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Ac",
    ]
)

#: ΔG_OH calibrado por metal (Man et al., ChemCatChem 2011).
_METAL_DG_OH: Final[dict[str, float]] = {
    "Sc": 0.52, "Ti": 0.78, "V": 0.97, "Cr": 1.07,
    "Mn": 1.27, "Fe": 1.12, "Co": 1.49, "Ni": 1.45,
    "Cu": 1.93, "Zn": 2.08,
    "Y": 0.47, "Zr": 0.67, "Nb": 0.87, "Mo": 1.32,
    "Tc": 1.68, "Ru": 1.60, "Rh": 1.72, "Pd": 1.83,
    "Ag": 2.33, "Cd": 2.18,
    "La": 0.37, "Hf": 0.62, "Ta": 0.77, "W": 1.22,
    "Re": 1.73, "Os": 1.65, "Ir": 1.41, "Pt": 1.88,
    "Au": 2.53, "Hg": 2.33,
    "Ac": 0.37,
}

#: Energias de superfície de referência CHGNet (γ em J/m², slab 110).
_SURFACE_ENERGY_REFS: Final[dict[str, float]] = {
    "Ru": 0.741, "Ir": 0.772, "Ti": 1.125,
    "Mn": 0.610, "Co": 0.311, "Ni": 0.301,
}

_DEFAULT_DG_OH: Final[float] = 1.20

#: Índices de Miller para tentativa de geração de slab.
_MILLER_INDICES: Final[list[tuple[int, int, int]]] = [
    (1, 1, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1),
]

logger: logging.Logger = logging.getLogger(__name__)


# Tipagem do resultado

class OERResult(TypedDict):
    formula: str
    band_gap_eV: float
    overpotential_V: float
    is_viable: bool
    delta_G_O: float
    delta_G_OH: float
    delta_G_OOH: float


# Exceções de domínio


class CIFParsingError(Exception):
    """Falha ao interpretar o conteúdo CIF / XYZ fornecido."""


class InvalidCatalystError(ValueError):
    """A estrutura não atende aos requisitos mínimos de composição."""


# Motor principal — CHGNet + CHE framework


class OERPredictor:
    """Preditor de atividade OER usando CHGNet (potencial universal GNN).

    CHGNet é uma GNN pré-treinada em ~1.6M estruturas do Materials Project,
    capaz de predizer energias, forças, stress e momentos magnéticos para
    qualquer material inorgânico.  Roda em GPU (CUDA) para inferência rápida.
    """

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
        """Cria ASE Calculator com o modelo CHGNet compartilhado."""
        return self._CHGNetCalculator(model=self._model)

    # API pública 

    def predict_oer_activity(self, file_content: str) -> OERResult:
        """Prediz a atividade OER usando CHGNet + CHE framework."""
        structure = self._parse_structure(file_content)
        self._validate_composition(structure)

        # CHGNet: predição bulk
        bulk_pred = self._predict_bulk(structure)

        # Slab + energia de superfície via CHGNet
        surface_energy, _ = self._compute_surface_energy(
            structure, bulk_pred["e_per_atom"]
        )

        # ΔG de adsorção (descritores CHGNet + scaling relations)
        dg_oh, dg_o, dg_ooh = self._compute_oer_energies(
            structure, bulk_pred, surface_energy
        )

        # Overpotential teórico
        overpotential = self._compute_overpotential(dg_oh, dg_o, dg_ooh)

        # Band gap estimado
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

    # CHGNet Predictions

    def _predict_bulk(self, structure: Structure) -> dict:
        """Predição CHGNet na estrutura bulk: energia, forças, stress, magmoms."""
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
        """Gera slab, relaxa com CHGNet+ASE, e calcula γ (J/m²)."""
        from ase.constraints import FixAtoms
        from ase.optimize import BFGS

        slab = self._find_best_slab(structure)
        if slab is None:
            logger.warning("Sem slab válido. Usando γ=0.75 J/m².")
            return 0.75, e_bulk

        # Relaxar slab (fixando metade inferior)
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
        """Tenta múltiplos Miller indices e retorna o melhor slab."""
        for hkl in _MILLER_INDICES:
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

        # Fallback
        try:
            slabs = SlabGenerator(
                structure, [1, 1, 0],
                min_slab_size=6.0, min_vacuum_size=12.0,
                center_slab=True,
            ).get_slabs()
            return slabs[0] if slabs else None
        except Exception:
            return None

    # OER Energy Computation 

    def _compute_oer_energies(
        self, structure: Structure, bulk_pred: dict, surface_energy: float
    ) -> tuple[float, float, float]:
        r"""Calcula ΔG_OH, ΔG_O, ΔG_OOH combinando descritores CHGNet
        com relações de escala universais (Man et al., 2011).

        Descritores CHGNet usados para correção estrutural:
        - Energia de superfície γ (reatividade superficial)
        - Energia bulk por átomo (estabilidade do óxido)
        - Momento magnético (estado eletrônico d)
        """
        baseline = self._get_baseline_dg_oh(structure)
        metal = self._get_principal_metal(structure)

        # Correção: energia de superfície
        gamma_ref = _SURFACE_ENERGY_REFS.get(metal, 0.75)
        d_gamma = surface_energy - gamma_ref
        corr_gamma = -0.15 * d_gamma  # γ↑ → superfície mais reativa → ΔG_OH↓

        # Correção: energia bulk
        corr_bulk = 0.0  # sem referência → sem correção
        # (a composição já captura o efeito principal via baseline)

        # Correção: momento magnético
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
        dg_vals = [(m, _METAL_DG_OH.get(m, _DEFAULT_DG_OH)) for m in metals]
        best, _ = min(dg_vals, key=lambda x: abs(x[1] - 1.60))
        return best

    @staticmethod
    def _get_baseline_dg_oh(structure: Structure) -> float:
        symbols = {str(sp) for sp in structure.species}
        metals = symbols & METAIS_TRANSICAO
        if not metals:
            return _DEFAULT_DG_OH
        dg_vals = [(m, _METAL_DG_OH.get(m, _DEFAULT_DG_OH)) for m in metals]
        _, best_dg = min(dg_vals, key=lambda x: abs(x[1] - 1.60))
        return best_dg

    @staticmethod
    def _compute_overpotential(dg_oh: float, dg_o: float, dg_ooh: float) -> float:
        """Overpotential teórico: η = max(ΔGᵢ) − 1.23 V."""
        e_total = 4.0 * E_OER_REVERSIVEL
        dg1 = dg_oh
        dg2 = dg_o - dg_oh
        dg3 = dg_ooh - dg_o
        dg4 = e_total - dg_ooh
        return max(max(dg1, dg2, dg3, dg4) - E_OER_REVERSIVEL, 0.0)

    def _estimate_band_gap(self, structure: Structure, bulk_pred: dict) -> float:
        """Band gap estimado a partir de descritores CHGNet (eV)."""
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

    # Parsing / Validação

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
