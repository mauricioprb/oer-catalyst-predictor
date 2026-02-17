from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from torch.optim import Optimizer
from torch.utils.data import DataLoader

from ml.modelo import DetectorFraudeMEV

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class MetricasEpoca:
    epoca: int
    perda_treino: float
    acuracia_treino: float
    perda_validacao: float
    acuracia_validacao: float
    duracao_segundos: float
    learning_rate: float

    def to_dict(self) -> dict:
        return {
            "epoca": self.epoca,
            "perda_treino": round(self.perda_treino, 6),
            "acuracia_treino": round(self.acuracia_treino, 4),
            "perda_validacao": round(self.perda_validacao, 6),
            "acuracia_validacao": round(self.acuracia_validacao, 4),
            "duracao_segundos": round(self.duracao_segundos, 2),
            "learning_rate": self.learning_rate,
        }


@dataclass
class HistoricoTreinamento:
    epocas: list[MetricasEpoca] = field(default_factory=list)
    melhor_acuracia_validacao: float = 0.0
    melhor_epoca: int = 0

    def registrar(self, metricas: MetricasEpoca) -> bool:
        self.epocas.append(metricas)
        houve_melhora: bool = (
            metricas.acuracia_validacao > self.melhor_acuracia_validacao
        )
        if houve_melhora:
            self.melhor_acuracia_validacao = metricas.acuracia_validacao
            self.melhor_epoca = metricas.epoca
        return houve_melhora

    def to_dict(self) -> dict:
        return {
            "melhor_acuracia_validacao": round(self.melhor_acuracia_validacao, 4),
            "melhor_epoca": self.melhor_epoca,
            "total_epocas": len(self.epocas),
            "epocas": [e.to_dict() for e in self.epocas],
        }


class GerenciadorTreinamento:

    def __init__(
        self,
        modelo: DetectorFraudeMEV,
        carregador_treino: DataLoader,
        carregador_validacao: DataLoader,
        otimizador: Optimizer,
        funcao_perda: nn.Module,
        caminho_artefatos: Path | str = Path("/app/armazenamento/pesos"),
        agendador_lr: Optional[torch.optim.lr_scheduler.LRScheduler] = None,
        paciencia_early_stop: int = 10,
    ) -> None:
        self.dispositivo: torch.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.modelo: DetectorFraudeMEV = modelo.to(self.dispositivo)
        self.carregador_treino: DataLoader = carregador_treino
        self.carregador_validacao: DataLoader = carregador_validacao
        self.otimizador: Optimizer = otimizador
        self.funcao_perda: nn.Module = funcao_perda.to(self.dispositivo)
        self.caminho_artefatos: Path = Path(caminho_artefatos)
        self.agendador_lr: Optional[torch.optim.lr_scheduler.LRScheduler] = (
            agendador_lr
        )
        self.paciencia_early_stop: int = paciencia_early_stop

        self.historico: HistoricoTreinamento = HistoricoTreinamento()
        self._contador_sem_melhora: int = 0

        self.caminho_artefatos.mkdir(parents=True, exist_ok=True)

        logger.info("Dispositivo selecionado: %s", self.dispositivo)
        logger.info("Parâmetros do modelo: %s", modelo.contar_parametros())

    def _obter_learning_rate(self) -> float:
        grupo: dict = self.otimizador.param_groups[0]
        taxa: float = grupo["lr"]
        return taxa

    def executar_epoca_treino(self) -> tuple[float, float]:
        self.modelo.train()

        perda_acumulada: float = 0.0
        acertos_totais: int = 0
        amostras_totais: int = 0

        lote_imagens: torch.Tensor
        lote_rotulos: torch.Tensor

        for lote_imagens, lote_rotulos in self.carregador_treino:
            lote_imagens = lote_imagens.to(self.dispositivo, non_blocking=True)
            lote_rotulos = lote_rotulos.float().to(
                self.dispositivo, non_blocking=True
            )

            self.otimizador.zero_grad(set_to_none=True)

            logits: torch.Tensor = self.modelo(lote_imagens).squeeze(1)
            perda: torch.Tensor = self.funcao_perda(logits, lote_rotulos)

            perda.backward()
            torch.nn.utils.clip_grad_norm_(self.modelo.parameters(), max_norm=1.0)
            self.otimizador.step()

            perda_acumulada += perda.item() * lote_imagens.size(0)
            predicoes: torch.Tensor = (torch.sigmoid(logits) >= 0.5).float()
            acertos_totais += (predicoes == lote_rotulos).sum().item()
            amostras_totais += lote_imagens.size(0)

        perda_media: float = perda_acumulada / max(amostras_totais, 1)
        acuracia_media: float = acertos_totais / max(amostras_totais, 1)

        return perda_media, acuracia_media

    @torch.no_grad()
    def executar_epoca_validacao(self) -> tuple[float, float]:
        self.modelo.eval()

        perda_acumulada: float = 0.0
        acertos_totais: int = 0
        amostras_totais: int = 0

        lote_imagens: torch.Tensor
        lote_rotulos: torch.Tensor

        for lote_imagens, lote_rotulos in self.carregador_validacao:
            lote_imagens = lote_imagens.to(self.dispositivo, non_blocking=True)
            lote_rotulos = lote_rotulos.float().to(
                self.dispositivo, non_blocking=True
            )

            logits: torch.Tensor = self.modelo(lote_imagens).squeeze(1)
            perda: torch.Tensor = self.funcao_perda(logits, lote_rotulos)

            perda_acumulada += perda.item() * lote_imagens.size(0)
            predicoes: torch.Tensor = (torch.sigmoid(logits) >= 0.5).float()
            acertos_totais += (predicoes == lote_rotulos).sum().item()
            amostras_totais += lote_imagens.size(0)

        perda_media: float = perda_acumulada / max(amostras_totais, 1)
        acuracia_media: float = acertos_totais / max(amostras_totais, 1)

        return perda_media, acuracia_media

    def executar_epoca(self, numero_epoca: int) -> MetricasEpoca:
        import time

        marca_inicio: float = time.perf_counter()

        perda_treino: float
        acuracia_treino: float
        perda_treino, acuracia_treino = self.executar_epoca_treino()

        perda_validacao: float
        acuracia_validacao: float
        perda_validacao, acuracia_validacao = self.executar_epoca_validacao()

        marca_fim: float = time.perf_counter()
        duracao: float = marca_fim - marca_inicio

        if self.agendador_lr is not None:
            self.agendador_lr.step()

        metricas: MetricasEpoca = MetricasEpoca(
            epoca=numero_epoca,
            perda_treino=perda_treino,
            acuracia_treino=acuracia_treino,
            perda_validacao=perda_validacao,
            acuracia_validacao=acuracia_validacao,
            duracao_segundos=duracao,
            learning_rate=self._obter_learning_rate(),
        )

        logger.info(
            "Época %03d | Treino: perda=%.4f acc=%.4f | "
            "Validação: perda=%.4f acc=%.4f | %.1fs",
            numero_epoca,
            perda_treino,
            acuracia_treino,
            perda_validacao,
            acuracia_validacao,
            duracao,
        )

        return metricas

    def treinar(self, numero_epocas: int) -> HistoricoTreinamento:
        logger.info(
            "Iniciando treinamento: %d épocas, dispositivo=%s",
            numero_epocas,
            self.dispositivo,
        )

        for epoca in range(1, numero_epocas + 1):
            metricas: MetricasEpoca = self.executar_epoca(epoca)
            houve_melhora: bool = self.historico.registrar(metricas)

            if houve_melhora:
                self._contador_sem_melhora = 0
                self.salvar_artefatos(sufixo="melhor")
                logger.info(
                    "Nova melhor acurácia de validação: %.4f",
                    metricas.acuracia_validacao,
                )
            else:
                self._contador_sem_melhora += 1

            if self._contador_sem_melhora >= self.paciencia_early_stop:
                logger.info(
                    "Early stopping ativado na época %d "
                    "(sem melhora por %d épocas consecutivas)",
                    epoca,
                    self.paciencia_early_stop,
                )
                break

        self.salvar_artefatos(sufixo="final")
        self._salvar_historico()

        logger.info(
            "Treinamento concluído. Melhor validação: %.4f (época %d)",
            self.historico.melhor_acuracia_validacao,
            self.historico.melhor_epoca,
        )

        return self.historico

    def salvar_artefatos(self, sufixo: str = "") -> Path:
        carimbo_data: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo: str = f"detector_mev_{carimbo_data}"
        if sufixo:
            nome_arquivo = f"{nome_arquivo}_{sufixo}"
        nome_arquivo = f"{nome_arquivo}.pt"

        caminho_completo: Path = self.caminho_artefatos / nome_arquivo

        conteudo_checkpoint: dict = {
            "estado_modelo": self.modelo.state_dict(),
            "estado_otimizador": self.otimizador.state_dict(),
            "arquitetura": self.modelo.nome_arquitetura,
            "parametros_modelo": self.modelo.contar_parametros(),
            "historico": self.historico.to_dict(),
            "dispositivo_treino": str(self.dispositivo),
            "carimbo_data": carimbo_data,
        }

        if self.agendador_lr is not None:
            conteudo_checkpoint["estado_agendador"] = self.agendador_lr.state_dict()

        torch.save(conteudo_checkpoint, caminho_completo)
        logger.info("Artefato salvo: %s", caminho_completo)

        return caminho_completo

    def _salvar_historico(self) -> Path:
        carimbo_data: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_json: Path = (
            self.caminho_artefatos / f"historico_{carimbo_data}.json"
        )

        with open(caminho_json, "w", encoding="utf-8") as arquivo:
            json.dump(self.historico.to_dict(), arquivo, indent=2, ensure_ascii=False)

        logger.info("Histórico salvo: %s", caminho_json)
        return caminho_json

    @classmethod
    def carregar_checkpoint(
        cls,
        caminho_checkpoint: Path | str,
        modelo: DetectorFraudeMEV,
        otimizador: Optional[Optimizer] = None,
    ) -> dict:
        caminho: Path = Path(caminho_checkpoint)

        if not caminho.exists():
            raise FileNotFoundError(f"Checkpoint não encontrado: {caminho}")

        dispositivo: torch.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        checkpoint: dict = torch.load(caminho, map_location=dispositivo, weights_only=False)

        modelo.load_state_dict(checkpoint["estado_modelo"])
        modelo.to(dispositivo)

        if otimizador is not None and "estado_otimizador" in checkpoint:
            otimizador.load_state_dict(checkpoint["estado_otimizador"])

        logger.info(
            "Checkpoint carregado: %s (dispositivo=%s)", caminho, dispositivo
        )

        return checkpoint
