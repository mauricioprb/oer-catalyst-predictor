from __future__ import annotations

from typing import Final

E_OER_REVERSIVEL: Final[float] = 1.23

LIMIAR_OVERPOTENTIAL: Final[float] = 0.40

METAIS_TRANSICAO: Final[frozenset[str]] = frozenset(
    [
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "La", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Ac",
    ]
)

METAL_DG_OH: Final[dict[str, float]] = {
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

SURFACE_ENERGY_REFS: Final[dict[str, float]] = {
    "Ru": 0.741, "Ir": 0.772, "Ti": 1.125,
    "Mn": 0.610, "Co": 0.311, "Ni": 0.301,
}

DEFAULT_DG_OH: Final[float] = 1.20

MILLER_INDICES: Final[list[tuple[int, int, int]]] = [
    (1, 1, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1),
]
