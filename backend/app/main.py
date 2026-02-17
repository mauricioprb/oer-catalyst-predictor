from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.core.servidor import ServidorAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncGenerator[None, None]:
    ServidorAPI.carregar_modelo()
    yield
    ServidorAPI.liberar_modelo()


app: FastAPI = FastAPI(
    title="Nanoxus — Detecção de Fraude em Microscopia Eletrônica",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    modelo_carregado: bool = ServidorAPI.obter_modelo() is not None
    return {
        "status": "ok",
        "modelo_carregado": str(modelo_carregado),
        "dispositivo": str(ServidorAPI.obter_dispositivo()),
    }
