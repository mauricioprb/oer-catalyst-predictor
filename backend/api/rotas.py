from __future__ import annotations

import io
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from app.core.config import settings
from app.core.servidor import ServidorAPI
from ml.modelo import ArquiteturaBase, DetectorFraudeMEV
from ml.processamento_dados import CarregadorDataset, ProcessadorImagem
from ml.treinador import GerenciadorTreinamento

logger: logging.Logger = logging.getLogger(__name__)

router: APIRouter = APIRouter()


class RespostaAnalise(BaseModel):
    probabilidade_fraude: float
    classe_predita: str
    tempo_inferencia_ms: float
    nome_arquivo: str
    dimensoes_originais: list[int]


class RespostaTreinamento(BaseModel):
    id_tarefa: str
    mensagem: str
    data_inicio: str


class ParametrosTreinamento(BaseModel):
    epochs: int = 30
    batch_size: int = 32
    learning_rate: float = 1e-4
    arquitetura: str = "resnet18"
    use_mock: bool = False
    early_stop_patience: int = 10


_tarefas_treinamento: dict[str, dict] = {}


@router.post("/analisar-imagem", response_model=RespostaAnalise)
async def analisar_imagem(arquivo: UploadFile) -> RespostaAnalise:
    modelo: Optional[DetectorFraudeMEV] = ServidorAPI.obter_modelo()

    if modelo is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo não carregado. Realize o treinamento primeiro.",
        )

    extensoes_permitidas: set[str] = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    nome_arquivo: str = arquivo.filename or "imagem_sem_nome"
    extensao: str = Path(nome_arquivo).suffix.lower()

    if extensao not in extensoes_permitidas:
        raise HTTPException(
            status_code=422,
            detail=f"Formato não suportado: {extensao}. "
            f"Use: {', '.join(extensoes_permitidas)}",
        )

    conteudo_bytes: bytes = await arquivo.read()

    try:
        imagem_pil: Image.Image = Image.open(io.BytesIO(conteudo_bytes))
        largura: int = imagem_pil.width
        altura: int = imagem_pil.height
        imagem_array: np.ndarray = np.array(imagem_pil.convert("RGB"))
    except Exception as erro:
        raise HTTPException(
            status_code=422,
            detail=f"Não foi possível decodificar a imagem: {erro}",
        )

    dispositivo: torch.device = ServidorAPI.obter_dispositivo()

    imagem_rgb: np.ndarray = ProcessadorImagem.converter_para_rgb(imagem_array)
    imagem_limpa: np.ndarray = ProcessadorImagem.remover_ruido(imagem_rgb)
    tensor_entrada: torch.Tensor = ProcessadorImagem.normalizar_para_tensor(
        imagem_limpa
    )
    tensor_entrada = tensor_entrada.unsqueeze(0).to(dispositivo)

    inicio_inferencia: float = time.perf_counter()

    modelo.eval()
    with torch.no_grad():
        logits: torch.Tensor = modelo(tensor_entrada)
        probabilidade: float = torch.sigmoid(logits).squeeze().item()

    fim_inferencia: float = time.perf_counter()
    tempo_inferencia_ms: float = (fim_inferencia - inicio_inferencia) * 1000

    classe_predita: str = "Sintética" if probabilidade >= 0.5 else "Real"

    logger.info(
        "Análise concluída: %s | P(fraude)=%.4f | Classe=%s | %.1fms",
        nome_arquivo,
        probabilidade,
        classe_predita,
        tempo_inferencia_ms,
    )

    return RespostaAnalise(
        probabilidade_fraude=round(probabilidade, 6),
        classe_predita=classe_predita,
        tempo_inferencia_ms=round(tempo_inferencia_ms, 2),
        nome_arquivo=nome_arquivo,
        dimensoes_originais=[largura, altura],
    )


def _executar_treinamento(id_tarefa: str, parametros: ParametrosTreinamento) -> None:
    _tarefas_treinamento[id_tarefa]["estado"] = "em_execucao"

    try:
        mapa_arquiteturas: dict[str, ArquiteturaBase] = {
            "resnet18": ArquiteturaBase.RESNET18,
            "resnet34": ArquiteturaBase.RESNET34,
            "efficientnet_b0": ArquiteturaBase.EFFICIENTNET_B0,
        }

        arquitetura: ArquiteturaBase = mapa_arquiteturas.get(
            parametros.arquitetura, ArquiteturaBase.RESNET18
        )

        modelo: DetectorFraudeMEV = DetectorFraudeMEV(
            arquitetura=arquitetura, pretrained=True
        )

        carregador: CarregadorDataset = CarregadorDataset(
            caminho_reais=settings.DADOS_REAIS_PATH,
            caminho_sinteticas=settings.DADOS_SINTETICAS_PATH,
            tamanho_lote=parametros.batch_size,
        )

        carregador.preparar_transformacoes(modo_treino=True)
        carregador_treino, carregador_validacao = carregador.carregar_imagens(
            usar_mock=parametros.use_mock
        )

        dispositivo: torch.device = ServidorAPI.obter_dispositivo()
        modelo.to(dispositivo)

        otimizador: torch.optim.AdamW = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, modelo.parameters()),
            lr=parametros.learning_rate,
            weight_decay=1e-4,
        )

        funcao_perda: torch.nn.BCEWithLogitsLoss = torch.nn.BCEWithLogitsLoss()

        agendador: torch.optim.lr_scheduler.CosineAnnealingLR = (
            torch.optim.lr_scheduler.CosineAnnealingLR(
                otimizador, T_max=parametros.epochs, eta_min=1e-6
            )
        )

        gerenciador: GerenciadorTreinamento = GerenciadorTreinamento(
            modelo=modelo,
            carregador_treino=carregador_treino,
            carregador_validacao=carregador_validacao,
            otimizador=otimizador,
            funcao_perda=funcao_perda,
            caminho_artefatos=settings.MODELO_PESOS_PATH,
            agendador_lr=agendador,
            paciencia_early_stop=parametros.early_stop_patience,
        )

        historico = gerenciador.treinar(numero_epocas=parametros.epochs)

        _tarefas_treinamento[id_tarefa]["estado"] = "concluido"
        _tarefas_treinamento[id_tarefa]["resultado"] = historico.to_dict()

        ServidorAPI.carregar_modelo()
        logger.info("Tarefa %s concluída. Modelo atualizado na memória.", id_tarefa)

    except Exception as erro:
        logger.exception("Falha na tarefa de treinamento %s", id_tarefa)
        _tarefas_treinamento[id_tarefa]["estado"] = "erro"
        _tarefas_treinamento[id_tarefa]["erro"] = str(erro)


@router.post("/iniciar-treinamento", response_model=RespostaTreinamento)
async def iniciar_treinamento(
    tarefas_background: BackgroundTasks,
    parametros: Optional[ParametrosTreinamento] = None,
) -> RespostaTreinamento:
    if parametros is None:
        parametros = ParametrosTreinamento()

    id_tarefa: str = uuid.uuid4().hex[:12]
    data_inicio: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _tarefas_treinamento[id_tarefa] = {
        "estado": "enfileirado",
        "data_inicio": data_inicio,
        "parametros": parametros.model_dump(),
        "resultado": None,
        "erro": None,
    }

    tarefas_background.add_task(_executar_treinamento, id_tarefa, parametros)

    logger.info("Treinamento enfileirado: tarefa=%s", id_tarefa)

    return RespostaTreinamento(
        id_tarefa=id_tarefa,
        mensagem="Treinamento iniciado em background",
        data_inicio=data_inicio,
    )


@router.get("/treinamento/{id_tarefa}")
async def consultar_treinamento(id_tarefa: str) -> dict:
    if id_tarefa not in _tarefas_treinamento:
        raise HTTPException(
            status_code=404,
            detail=f"Tarefa não encontrada: {id_tarefa}",
        )
    return _tarefas_treinamento[id_tarefa]
