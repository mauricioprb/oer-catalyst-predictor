from __future__ import annotations

from fastapi import APIRouter

from app.core.lifespan import get_predictor

router: APIRouter = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "predictor_loaded": get_predictor() is not None,
    }
