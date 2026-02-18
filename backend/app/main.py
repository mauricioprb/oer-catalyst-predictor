"""
main.py — Ponto de entrada da API Nanoxus para Materials Informatics.

Serve endpoints REST via FastAPI/Uvicorn para predição de atividade OER
(Oxygen Evolution Reaction) a partir de arquivos de estrutura cristalina
(.cif, .xyz, .vasp).
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.domain.services.science_engine import (
    CIFParsingError,
    InvalidCatalystError,
    OERPredictor,
    OERResult,
)

# Logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger(__name__)

# Pydantic — modelos de resposta

from pydantic import BaseModel, Field


class AdsorptionEnergies(BaseModel):
    """Energias livres de Gibbs de adsorção dos intermediários OER (eV)."""

    delta_G_O: float = Field(..., description="ΔG de adsorção do *O (eV)")
    delta_G_OH: float = Field(..., description="ΔG de adsorção do *OH (eV)")
    delta_G_OOH: float = Field(..., description="ΔG de adsorção do *OOH (eV)")


class PredictionResponse(BaseModel):
    """Resposta completa do endpoint /api/predict."""

    formula: str = Field(..., description="Fórmula química reduzida do material")
    band_gap_eV: float = Field(..., description="Band gap estimado (eV)")
    overpotential_V: float = Field(
        ..., description="Overpotential teórico OER (V)"
    )
    is_viable: bool = Field(
        ...,
        description="True se overpotential < 0.40 V (catalisador promissor)",
    )
    adsorption_energies: AdsorptionEnergies
    inference_time_ms: float = Field(
        ..., description="Tempo de inferência em milissegundos"
    )
    filename: str = Field(..., description="Nome do arquivo enviado")


class ErrorResponse(BaseModel):
    """Corpo padrão de respostas de erro."""

    detail: str


# Instância global do preditor OER

_predictor: OERPredictor | None = None

EXTENSOES_PERMITIDAS: frozenset[str] = frozenset({".cif", ".xyz", ".vasp"})


# Ciclo de vida da aplicação


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa o OERPredictor no startup e libera recursos no shutdown."""
    global _predictor  # noqa: PLW0603
    logger.info("Inicializando OERPredictor …")
    _predictor = OERPredictor()
    logger.info("OERPredictor pronto.")
    yield
    _predictor = None
    logger.info("OERPredictor liberado.")


# Aplicação FastAPI

app: FastAPI = FastAPI(
    title="Nanoxus — Materials Informatics & OER Prediction",
    version="1.0.0",
    description=(
        "API para predição de atividade eletrocatalítica (OER) "
        "a partir de estruturas cristalinas via CHGNet "
        "(Crystal Hamiltonian Graph Neural Network, 412k params, GPU)."
    ),
    lifespan=ciclo_de_vida,
    responses={
        400: {"model": ErrorResponse, "description": "Arquivo corrompido"},
        422: {"model": ErrorResponse, "description": "Formato inválido"},
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints


@app.get("/health")
def health_check() -> dict[str, str | bool]:
    """Verifica o estado da API e do preditor."""
    return {
        "status": "ok",
        "predictor_loaded": _predictor is not None,
    }


@app.post(
    "/api/predict",
    response_model=PredictionResponse,
    summary="Predição de atividade OER",
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def predict_oer(arquivo: UploadFile) -> PredictionResponse:
    """Recebe um arquivo de estrutura cristalina e retorna a predição OER.

    Formatos aceitos: **.cif**, **.xyz**, **.vasp**.
    """
    # Garantir que o preditor está carregado
    if _predictor is None:
        raise HTTPException(
            status_code=503,
            detail="OERPredictor não inicializado. Tente novamente em instantes.",
        )

    # Validação de extensão
    nome_arquivo: str = arquivo.filename or "unknown"
    extensao: str = Path(nome_arquivo).suffix.lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Formato não suportado: '{extensao}'. "
                f"Extensões aceitas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}."
            ),
        )

    # Leitura do conteúdo
    try:
        conteudo_bytes: bytes = await arquivo.read()
        conteudo: str = conteudo_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"O arquivo não é texto UTF-8 válido: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Falha ao ler o arquivo: {exc}",
        )

    if not conteudo.strip():
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado está vazio.",
        )

    # Inferência via threadpool (não bloqueia o event loop)
    inicio: float = time.perf_counter()

    try:
        resultado: OERResult = await run_in_threadpool(
            _predictor.predict_oer_activity, conteudo
        )
    except CIFParsingError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível interpretar o arquivo: {exc}",
        )
    except InvalidCatalystError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Estrutura inválida para análise OER: {exc}",
        )
    except Exception as exc:
        logger.exception("Erro inesperado durante a predição")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno durante a predição: {exc}",
        )

    tempo_ms: float = (time.perf_counter() - inicio) * 1000

    logger.info(
        "Predição concluída: %s | η=%.4f V | viável=%s | %.1f ms",
        resultado["formula"],
        resultado["overpotential_V"],
        resultado["is_viable"],
        tempo_ms,
    )

    return PredictionResponse(
        formula=resultado["formula"],
        band_gap_eV=resultado["band_gap_eV"],
        overpotential_V=resultado["overpotential_V"],
        is_viable=resultado["is_viable"],
        adsorption_energies=AdsorptionEnergies(
            delta_G_O=resultado["delta_G_O"],
            delta_G_OH=resultado["delta_G_OH"],
            delta_G_OOH=resultado["delta_G_OOH"],
        ),
        inference_time_ms=round(tempo_ms, 2),
        filename=nome_arquivo,
    )
