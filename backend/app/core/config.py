from __future__ import annotations

import logging
from typing import Final

EXTENSOES_PERMITIDAS: Final[frozenset[str]] = frozenset({".cif", ".xyz", ".vasp"})

APP_TITLE: Final[str] = "Nanoxus - OER Catalyst Predictor"
APP_VERSION: Final[str] = "1.0.0"
APP_DESCRIPTION: Final[str] = (
    "API para predição de atividade eletrocatalítica (OER) "
    "a partir de estruturas cristalinas via CHGNet "
    "(Crystal Hamiltonian Graph Neural Network, 412k params, GPU)."
)

CORS_ORIGINS: Final[list[str]] = ["http://localhost:3000", "*"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
