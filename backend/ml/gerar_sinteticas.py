"""
Script para gerar imagens sintéticas MEV a partir do gerador WGAN-GP treinado.

Uso:
    docker compose exec api_nanoxus python -m ml.gerar_sinteticas \
        --checkpoint /app/armazenamento/checkpoints_gan/gerador_final.pt \
        --quantidade 1000 \
        --saida /app/armazenamento/sinteticas_gan

As imagens geradas podem ser usadas para retreinar o detector de fraudes.
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from ml.gerador import carregar_gerador

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger(__name__)


def gerar_imagens(
    caminho_checkpoint: Path,
    diretorio_saida: Path,
    quantidade: int = 1000,
    tamanho_lote: int = 64,
    largura_final: int = 1024,
    altura_final: int = 768,
    semente: int | None = None,
) -> None:
    """Gera imagens sintéticas em escala de cinza usando o gerador treinado."""

    dispositivo: torch.device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    logger.info("Dispositivo: %s", dispositivo)

    # Carregar gerador
    gerador = carregar_gerador(caminho_checkpoint, dispositivo)
    dimensao_latente: int = gerador.dimensao_latente

    diretorio_saida.mkdir(parents=True, exist_ok=True)

    if semente is not None:
        torch.manual_seed(semente)

    redimensionar = transforms.Resize(
        (altura_final, largura_final),
        interpolation=transforms.InterpolationMode.BICUBIC,
        antialias=True,
    )

    geradas: int = 0
    inicio: float = time.time()

    logger.info(
        "Gerando %d imagens (%dx%d) em lotes de %d...",
        quantidade,
        largura_final,
        altura_final,
        tamanho_lote,
    )

    while geradas < quantidade:
        tam_lote_atual: int = min(tamanho_lote, quantidade - geradas)

        z: torch.Tensor = torch.randn(
            tam_lote_atual, dimensao_latente, 1, 1, device=dispositivo
        )

        with torch.no_grad():
            imagens: torch.Tensor = gerador(z)  # (N, 1, 256, 256), [-1, 1]
            imagens = (imagens + 1) / 2  # [0, 1]
            imagens = imagens.clamp(0, 1)
            imagens = redimensionar(imagens)

        for i in range(tam_lote_atual):
            indice: int = geradas + i
            # Converter tensor -> PIL -> salvar
            tensor_img: torch.Tensor = imagens[i].squeeze(0)  # (H, W)
            array_img = (tensor_img.cpu().numpy() * 255).astype("uint8")
            pil_img: Image.Image = Image.fromarray(array_img, mode="L")

            nome: str = f"GAN_{indice:04d}.jpg"
            pil_img.save(
                diretorio_saida / nome,
                quality=95,
            )

        geradas += tam_lote_atual

        if geradas % 200 == 0 or geradas == quantidade:
            logger.info("Progresso: %d/%d imagens", geradas, quantidade)

    duracao: float = time.time() - inicio
    logger.info(
        "Geração concluída: %d imagens em %.1fs (%.1f img/s)",
        quantidade,
        duracao,
        quantidade / duracao,
    )
    logger.info("Salvas em: %s", diretorio_saida)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Gerar imagens MEV sintéticas com WGAN-GP treinado",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="/app/armazenamento/checkpoints_gan/gerador_final.pt",
        help="Caminho do checkpoint do gerador",
    )
    parser.add_argument(
        "--saida",
        type=str,
        default="/app/armazenamento/sinteticas_gan",
        help="Diretório de saída das imagens geradas",
    )
    parser.add_argument("--quantidade", type=int, default=1000)
    parser.add_argument("--lote", type=int, default=64)
    parser.add_argument("--largura", type=int, default=1024)
    parser.add_argument("--altura", type=int, default=768)
    parser.add_argument("--semente", type=int, default=None)

    args: argparse.Namespace = parser.parse_args()

    gerar_imagens(
        caminho_checkpoint=Path(args.checkpoint),
        diretorio_saida=Path(args.saida),
        quantidade=args.quantidade,
        tamanho_lote=args.lote,
        largura_final=args.largura,
        altura_final=args.altura,
        semente=args.semente,
    )


if __name__ == "__main__":
    main()
