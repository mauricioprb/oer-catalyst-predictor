from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.schemas import AdsorptionEnergies, ErrorResponse, PredictionResponse
from app.core.config import EXTENSOES_PERMITIDAS
from app.core.lifespan import get_predictor
from app.domain.exceptions import CIFParsingError, InvalidCatalystError
from app.domain.services.oer_predictor import OERResult

logger: logging.Logger = logging.getLogger(__name__)

router: APIRouter = APIRouter(prefix="/api", tags=["prediction"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predição de atividade OER",
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def predict_oer(arquivo: UploadFile) -> PredictionResponse:
    predictor = get_predictor()

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="OERPredictor não inicializado. Tente novamente em instantes.",
        )

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

    inicio: float = time.perf_counter()

    try:
        resultado: OERResult = await run_in_threadpool(
            predictor.predict_oer_activity, conteudo
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
