from fastapi import APIRouter

from api.rotas import router as rotas_analise

router = APIRouter()

router.include_router(rotas_analise, tags=["análise"])


@router.get("/status")
def get_status():
    return {"servico": "nanoxus", "estado": "operacional"}
