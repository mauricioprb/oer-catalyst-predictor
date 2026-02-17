from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import torch

from app.core.config import settings
from ml.modelo import ArquiteturaBase, DetectorFraudeMEV

logger: logging.Logger = logging.getLogger(__name__)


class ServidorAPI:

    _instancia: Optional[ServidorAPI] = None
    _modelo: Optional[DetectorFraudeMEV] = None
    _dispositivo: Optional[torch.device] = None

    def __new__(cls) -> ServidorAPI:
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def obter_modelo(cls) -> Optional[DetectorFraudeMEV]:
        return cls._modelo

    @classmethod
    def obter_dispositivo(cls) -> torch.device:
        if cls._dispositivo is None:
            cls._dispositivo = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        return cls._dispositivo

    @classmethod
    def _encontrar_melhor_checkpoint(cls) -> Optional[Path]:
        caminho_pesos: Path = settings.MODELO_PESOS_PATH
        if not caminho_pesos.exists():
            return None

        checkpoints_melhor: list[Path] = sorted(
            caminho_pesos.glob("*_melhor.pt"), reverse=True
        )
        if checkpoints_melhor:
            return checkpoints_melhor[0]

        checkpoints_final: list[Path] = sorted(
            caminho_pesos.glob("*_final.pt"), reverse=True
        )
        if checkpoints_final:
            return checkpoints_final[0]

        todos_checkpoints: list[Path] = sorted(
            caminho_pesos.glob("*.pt"), reverse=True
        )
        if todos_checkpoints:
            return todos_checkpoints[0]

        return None

    @classmethod
    def carregar_modelo(cls) -> None:
        dispositivo: torch.device = cls.obter_dispositivo()
        logger.info("Dispositivo de inferência: %s", dispositivo)

        cls._modelo = DetectorFraudeMEV(
            arquitetura=ArquiteturaBase.RESNET18,
            pretrained=True,
        )

        caminho_checkpoint: Optional[Path] = cls._encontrar_melhor_checkpoint()

        if caminho_checkpoint is not None:
            logger.info("Carregando checkpoint: %s", caminho_checkpoint)
            checkpoint: dict = torch.load(
                caminho_checkpoint, map_location=dispositivo, weights_only=False
            )
            cls._modelo.load_state_dict(checkpoint["estado_modelo"])
            logger.info("Modelo restaurado com sucesso")
        else:
            logger.info(
                "Nenhum checkpoint encontrado — modelo inicializado com pesos ImageNet"
            )

        cls._modelo.to(dispositivo)
        cls._modelo.eval()

    @classmethod
    def liberar_modelo(cls) -> None:
        cls._modelo = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Modelo liberado da memória")
