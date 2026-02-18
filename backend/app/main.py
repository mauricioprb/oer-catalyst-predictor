from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.config  # noqa: F401
from app.api.routes.health import router as health_router
from app.api.routes.prediction import router as prediction_router
from app.api.schemas import ErrorResponse
from app.core.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION, CORS_ORIGINS
from app.core.lifespan import lifespan

app: FastAPI = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse, "description": "Arquivo corrompido"},
        422: {"model": ErrorResponse, "description": "Formato inválido"},
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(prediction_router)
