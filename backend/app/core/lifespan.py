from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.domain.services.oer_predictor import OERPredictor

logger: logging.Logger = logging.getLogger(__name__)

_predictor: OERPredictor | None = None


def get_predictor() -> OERPredictor | None:
    return _predictor


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    global _predictor
    logger.info("Inicializando OERPredictor …")
    _predictor = OERPredictor()
    logger.info("OERPredictor pronto.")
    yield
    _predictor = None
    logger.info("OERPredictor liberado.")
