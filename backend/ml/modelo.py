from __future__ import annotations

from enum import Enum
from typing import Optional

import torch
import torch.nn as nn
from torchvision import models
from torchvision.models import (
    EfficientNet_B0_Weights,
    ResNet18_Weights,
    ResNet34_Weights,
)


class ArquiteturaBase(Enum):
    RESNET18 = "resnet18"
    RESNET34 = "resnet34"
    EFFICIENTNET_B0 = "efficientnet_b0"


class DetectorFraudeMEV(nn.Module):

    def __init__(
        self,
        arquitetura: ArquiteturaBase = ArquiteturaBase.RESNET18,
        taxa_dropout: float = 0.4,
        camadas_descongeladas: int = 2,
        pretrained: bool = True,
    ) -> None:
        super().__init__()

        self.nome_arquitetura: str = arquitetura.value
        self.taxa_dropout: float = taxa_dropout
        self.camadas_descongeladas: int = camadas_descongeladas

        self.extrator_caracteristicas: nn.Module
        self.dimensao_entrada_classificador: int

        self.extrator_caracteristicas, self.dimensao_entrada_classificador = (
            self._construir_extrator(arquitetura, pretrained)
        )

        self._congelar_camadas()

        self.classificador: nn.Sequential = self._construir_classificador(
            self.dimensao_entrada_classificador, taxa_dropout
        )

    def _construir_extrator(
        self, arquitetura: ArquiteturaBase, pretrained: bool
    ) -> tuple[nn.Module, int]:
        if arquitetura == ArquiteturaBase.RESNET18:
            pesos: Optional[ResNet18_Weights] = (
                ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
            )
            modelo_base: nn.Module = models.resnet18(weights=pesos)
            dimensao: int = modelo_base.fc.in_features
            modelo_base.fc = nn.Identity()
            return modelo_base, dimensao

        if arquitetura == ArquiteturaBase.RESNET34:
            pesos_r34: Optional[ResNet34_Weights] = (
                ResNet34_Weights.IMAGENET1K_V1 if pretrained else None
            )
            modelo_base = models.resnet34(weights=pesos_r34)
            dimensao = modelo_base.fc.in_features
            modelo_base.fc = nn.Identity()
            return modelo_base, dimensao

        if arquitetura == ArquiteturaBase.EFFICIENTNET_B0:
            pesos_eff: Optional[EfficientNet_B0_Weights] = (
                EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
            )
            modelo_base = models.efficientnet_b0(weights=pesos_eff)
            dimensao = modelo_base.classifier[1].in_features
            modelo_base.classifier = nn.Identity()
            return modelo_base, dimensao

        raise ValueError(f"Arquitetura não suportada: {arquitetura}")

    def _congelar_camadas(self) -> None:
        parametros_nomeados: list[tuple[str, nn.Parameter]] = list(
            self.extrator_caracteristicas.named_parameters()
        )

        total_parametros: int = len(parametros_nomeados)
        indice_corte: int = max(0, total_parametros - self.camadas_descongeladas)

        for i, (_, parametro) in enumerate(parametros_nomeados):
            parametro.requires_grad = i >= indice_corte

    def _construir_classificador(
        self, dimensao_entrada: int, taxa_dropout: float
    ) -> nn.Sequential:
        classificador: nn.Sequential = nn.Sequential(
            nn.Linear(dimensao_entrada, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=taxa_dropout),
            nn.Linear(256, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.Dropout(p=taxa_dropout * 0.5),
            nn.Linear(64, 1),
        )
        return classificador

    def forward(self, tensor_entrada: torch.Tensor) -> torch.Tensor:
        vetor_caracteristicas: torch.Tensor = self.extrator_caracteristicas(
            tensor_entrada
        )
        logits: torch.Tensor = self.classificador(vetor_caracteristicas)
        return logits

    def predizer(self, tensor_entrada: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            logits: torch.Tensor = self.forward(tensor_entrada)
            probabilidades: torch.Tensor = torch.sigmoid(logits)
        return probabilidades

    def descongelar_tudo(self) -> None:
        for parametro in self.extrator_caracteristicas.parameters():
            parametro.requires_grad = True

    def contar_parametros(self) -> dict[str, int]:
        total: int = sum(p.numel() for p in self.parameters())
        treinaveis: int = sum(
            p.numel() for p in self.parameters() if p.requires_grad
        )
        congelados: int = total - treinaveis

        return {
            "total": total,
            "treinaveis": treinaveis,
            "congelados": congelados,
        }

    def __repr__(self) -> str:
        contagem: dict[str, int] = self.contar_parametros()
        return (
            f"DetectorFraudeMEV("
            f"arquitetura={self.nome_arquitetura}, "
            f"parametros_treinaveis={contagem['treinaveis']:,}, "
            f"parametros_congelados={contagem['congelados']:,})"
        )
