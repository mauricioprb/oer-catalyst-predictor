"""
Gerador de imagens sintéticas de MEV via WGAN-GP com Self-Attention.

Arquitetura melhorada em relação ao DCGAN original:
 - Perda Wasserstein com penalidade de gradiente (sem mode collapse)
 - Self-attention para capturar estruturas de longo alcance (nanofios, grãos)
 - Normalização espectral no crítico (gradientes bem-comportados)
 - Bloco residual de refinamento (detalhes texturais)
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils import spectral_norm

logger: logging.Logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Módulos auxiliares
# ---------------------------------------------------------------------------


class AutoAtencao(nn.Module):
    """Self-attention (SA-GAN) para capturar dependências espaciais longas."""

    def __init__(self, canais: int) -> None:
        super().__init__()
        self.query: nn.Conv2d = nn.Conv2d(canais, canais // 8, 1)
        self.chave: nn.Conv2d = nn.Conv2d(canais, canais // 8, 1)
        self.valor: nn.Conv2d = nn.Conv2d(canais, canais, 1)
        self.gamma: nn.Parameter = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.size()
        q = self.query(x).view(B, -1, H * W).permute(0, 2, 1)  # (B, HW, C//8)
        k = self.chave(x).view(B, -1, H * W)                     # (B, C//8, HW)
        atencao: torch.Tensor = torch.bmm(q, k)                   # (B, HW, HW)
        atencao = F.softmax(atencao, dim=-1)
        v = self.valor(x).view(B, -1, H * W)                     # (B, C, HW)
        saida: torch.Tensor = torch.bmm(v, atencao.permute(0, 2, 1))
        saida = saida.view(B, C, H, W)
        return self.gamma * saida + x


class BlocoResidual(nn.Module):
    """Bloco residual Conv-BN-ReLU-Conv-BN para refinar features."""

    def __init__(self, canais: int) -> None:
        super().__init__()
        self.bloco: nn.Sequential = nn.Sequential(
            nn.Conv2d(canais, canais, 3, 1, 1, bias=False),
            nn.BatchNorm2d(canais),
            nn.ReLU(inplace=True),
            nn.Conv2d(canais, canais, 3, 1, 1, bias=False),
            nn.BatchNorm2d(canais),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(x + self.bloco(x), inplace=True)


# ---------------------------------------------------------------------------
# Gerador (G) — WGAN-GP com Self-Attention
# ---------------------------------------------------------------------------


class GeradorWGAN(nn.Module):
    """Gerador que mapeia z (dim_latente, 1, 1) → imagem 256×256 cinza.

    Usa self-attention na resolução 32×32 para capturar estruturas globais
    (essencial para nanofios e texturas repetitivas de MEV) e um bloco
    residual para refinar detalhes texturais.
    """

    def __init__(self, dimensao_latente: int = 128) -> None:
        super().__init__()
        self.dimensao_latente: int = dimensao_latente

        # Caminho principal: z → 32×32
        self.rede: nn.Sequential = nn.Sequential(
            # 1×1 → 4×4
            nn.ConvTranspose2d(dimensao_latente, 1024, 4, 1, 0, bias=False),
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
            # 4×4 → 8×8
            nn.ConvTranspose2d(1024, 512, 4, 2, 1, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            # 8×8 → 16×16
            nn.ConvTranspose2d(512, 256, 4, 2, 1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            # 16×16 → 32×32
            nn.ConvTranspose2d(256, 128, 4, 2, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

        # Self-attention + refinamento na resolução 32×32
        self.atencao: AutoAtencao = AutoAtencao(128)
        self.refinamento: BlocoResidual = BlocoResidual(128)

        # Caminho de alta resolução: 32×32 → 256×256
        self.rede_alta: nn.Sequential = nn.Sequential(
            # 32×32 → 64×64
            nn.ConvTranspose2d(128, 64, 4, 2, 1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            # 64×64 → 128×128
            nn.ConvTranspose2d(64, 32, 4, 2, 1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            # 128×128 → 256×256  (1 canal, escala de cinza)
            nn.ConvTranspose2d(32, 1, 4, 2, 1, bias=False),
            nn.Tanh(),
        )

        self.apply(self._inicializar_pesos)

    @staticmethod
    def _inicializar_pesos(modulo: nn.Module) -> None:
        nome: str = modulo.__class__.__name__
        if "Conv" in nome:
            nn.init.normal_(modulo.weight.data, 0.0, 0.02)
        elif "BatchNorm" in nome:
            nn.init.normal_(modulo.weight.data, 1.0, 0.02)
            nn.init.constant_(modulo.bias.data, 0)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        x: torch.Tensor = self.rede(z)        # → (B, 128, 32, 32)
        x = self.atencao(x)                    # self-attention
        x = self.refinamento(x)                # bloco residual
        return self.rede_alta(x)               # → (B, 1, 256, 256)


# ---------------------------------------------------------------------------
# Crítico (D) — WGAN-GP com Normalização Espectral
# ---------------------------------------------------------------------------


class CriticoWGAN(nn.Module):
    """Crítico WGAN-GP com spectral norm e self-attention.

    Retorna score escalar SEM Sigmoid (necessário para Wasserstein loss).
    Usa spectral_norm em vez de BatchNorm (GP é incompatível com BN).
    """

    def __init__(self) -> None:
        super().__init__()

        # 256×256 → 32×32
        self.rede_baixa: nn.Sequential = nn.Sequential(
            # 256×256 → 128×128
            spectral_norm(nn.Conv2d(1, 32, 4, 2, 1)),
            nn.LeakyReLU(0.2, inplace=True),
            # 128×128 → 64×64
            spectral_norm(nn.Conv2d(32, 64, 4, 2, 1)),
            nn.LeakyReLU(0.2, inplace=True),
            # 64×64 → 32×32
            spectral_norm(nn.Conv2d(64, 128, 4, 2, 1)),
            nn.LeakyReLU(0.2, inplace=True),
        )

        # Self-attention na resolução 32×32
        self.atencao: AutoAtencao = AutoAtencao(128)

        # 32×32 → 1×1 (score escalar)
        self.rede_alta: nn.Sequential = nn.Sequential(
            # 32×32 → 16×16
            spectral_norm(nn.Conv2d(128, 256, 4, 2, 1)),
            nn.LeakyReLU(0.2, inplace=True),
            # 16×16 → 8×8
            spectral_norm(nn.Conv2d(256, 512, 4, 2, 1)),
            nn.LeakyReLU(0.2, inplace=True),
            # 8×8 → 4×4
            spectral_norm(nn.Conv2d(512, 1024, 4, 2, 1)),
            nn.LeakyReLU(0.2, inplace=True),
            # 4×4 → 1×1
            spectral_norm(nn.Conv2d(1024, 1, 4, 1, 0)),
        )

    def forward(self, imagem: torch.Tensor) -> torch.Tensor:
        x: torch.Tensor = self.rede_baixa(imagem)   # → (B, 128, 32, 32)
        x = self.atencao(x)                          # self-attention
        x = self.rede_alta(x)                        # → (B, 1, 1, 1)
        return x.view(-1)                            # → (B,)


# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------


def salvar_checkpoint_gerador(
    gerador: GeradorWGAN,
    caminho: Path,
    epoca: int,
    dimensao_latente: int,
) -> None:
    """Salva apenas o gerador (suficiente para gerar imagens)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "estado_gerador": gerador.state_dict(),
            "epoca": epoca,
            "dimensao_latente": dimensao_latente,
            "arquitetura": "wgan_gp_sa",
        },
        caminho,
    )
    logger.info("Checkpoint do gerador salvo: %s (época %d)", caminho, epoca)


def carregar_gerador(caminho: Path, dispositivo: torch.device) -> GeradorWGAN:
    """Carrega o gerador a partir de um checkpoint."""
    checkpoint: dict = torch.load(caminho, map_location=dispositivo, weights_only=True)
    dimensao_latente: int = checkpoint.get("dimensao_latente", 128)
    gerador: GeradorWGAN = GeradorWGAN(dimensao_latente=dimensao_latente)
    gerador.load_state_dict(checkpoint["estado_gerador"])
    gerador.to(dispositivo)
    gerador.eval()
    epoca: int = checkpoint.get("epoca", -1)
    logger.info("Gerador carregado: %s (época %d)", caminho, epoca)
    return gerador
