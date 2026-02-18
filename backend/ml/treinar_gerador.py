"""
Script de treinamento WGAN-GP com Self-Attention para geração de imagens MEV.

Melhorias em relação ao DCGAN original:
 - Wasserstein loss com gradient penalty (sem mode collapse)
 - Self-attention (captura estruturas globais como nanofios)
 - Normalização espectral no crítico
 - Treinamento mais estável e convergência mais suave

Uso dentro do container:
    python -m ml.treinar_gerador \
        --dados /app/armazenamento/reais \
        --epocas 500 \
        --lote 32

Ou externamente:
    docker compose exec api_nanoxus python -m ml.treinar_gerador \
        --dados /app/armazenamento/reais \
        --epocas 500
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import torch
import torch.autograd as autograd
from PIL import Image
from torch.optim import Adam
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.utils import save_image

from ml.gerador import (
    CriticoWGAN,
    GeradorWGAN,
    salvar_checkpoint_gerador,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger(__name__)

EXTENSOES_VALIDAS: set[str] = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class DatasetMEV(Dataset):
    """Carrega imagens MEV em escala de cinza com augmentação."""

    def __init__(self, diretorio: Path, tamanho: int = 256) -> None:
        self.caminhos: list[Path] = sorted(
            p
            for p in diretorio.iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSOES_VALIDAS
        )
        if not self.caminhos:
            raise FileNotFoundError(
                f"Nenhuma imagem encontrada em {diretorio}"
            )

        self.transformacao: transforms.Compose = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((tamanho, tamanho)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.3),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),  # [-1, 1]
        ])

    def __len__(self) -> int:
        return len(self.caminhos)

    def __getitem__(self, indice: int) -> torch.Tensor:
        imagem: Image.Image = Image.open(self.caminhos[indice]).convert("L")
        return self.transformacao(imagem)


# ---------------------------------------------------------------------------
# Penalidade de gradiente (WGAN-GP)
# ---------------------------------------------------------------------------


def calcular_penalidade_gradiente(
    critico: CriticoWGAN,
    reais: torch.Tensor,
    falsas: torch.Tensor,
    dispositivo: torch.device,
) -> torch.Tensor:
    """Calcula a penalidade de gradiente interpolando entre reais e falsas.

    Força a norma do gradiente do crítico a ficar próxima de 1 (condição de
    Lipschitz), o que estabiliza o treinamento Wasserstein.
    """
    alfa: torch.Tensor = torch.rand(reais.size(0), 1, 1, 1, device=dispositivo)
    interpolados: torch.Tensor = (
        alfa * reais + (1 - alfa) * falsas.detach()
    ).requires_grad_(True)

    saida_interpolada: torch.Tensor = critico(interpolados)

    gradientes: torch.Tensor = autograd.grad(
        outputs=saida_interpolada,
        inputs=interpolados,
        grad_outputs=torch.ones_like(saida_interpolada),
        create_graph=True,
        retain_graph=True,
    )[0]

    gradientes = gradientes.view(gradientes.size(0), -1)
    penalidade: torch.Tensor = ((gradientes.norm(2, dim=1) - 1) ** 2).mean()
    return penalidade


# ---------------------------------------------------------------------------
# Loop de treinamento WGAN-GP
# ---------------------------------------------------------------------------


def treinar_wgan_gp(
    diretorio_dados: Path,
    diretorio_saida: Path,
    epocas: int = 500,
    tamanho_lote: int = 32,
    dimensao_latente: int = 128,
    lr: float = 1e-4,
    n_critico: int = 5,
    lambda_gp: float = 10.0,
    intervalo_amostra: int = 25,
    intervalo_checkpoint: int = 50,
    tamanho_imagem: int = 256,
) -> None:
    """Treina o WGAN-GP com Self-Attention para geração de imagens MEV."""

    dispositivo: torch.device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    logger.info("Dispositivo: %s", dispositivo)

    # Diretórios de saída
    dir_amostras: Path = diretorio_saida / "amostras_gan"
    dir_checkpoints: Path = diretorio_saida / "checkpoints_gan"
    dir_amostras.mkdir(parents=True, exist_ok=True)
    dir_checkpoints.mkdir(parents=True, exist_ok=True)

    # Dataset
    dataset: DatasetMEV = DatasetMEV(diretorio_dados, tamanho=tamanho_imagem)
    logger.info("Imagens de treinamento: %d", len(dataset))

    carregador: DataLoader = DataLoader(
        dataset,
        batch_size=tamanho_lote,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        drop_last=True,
    )

    # Modelos
    gerador: GeradorWGAN = GeradorWGAN(
        dimensao_latente=dimensao_latente,
    ).to(dispositivo)
    critico: CriticoWGAN = CriticoWGAN().to(dispositivo)

    # Adam com beta1=0.0 (recomendação do paper WGAN-GP)
    otimizador_g: Adam = Adam(
        gerador.parameters(), lr=lr, betas=(0.0, 0.9)
    )
    otimizador_c: Adam = Adam(
        critico.parameters(), lr=lr, betas=(0.0, 0.9)
    )

    # Vetor latente fixo para visualizar progresso
    z_fixo: torch.Tensor = torch.randn(
        16, dimensao_latente, 1, 1, device=dispositivo
    )

    logger.info(
        "Iniciando WGAN-GP+SA — %d épocas, n_critico=%d, λ_gp=%.1f",
        epocas,
        n_critico,
        lambda_gp,
    )
    inicio_total: float = time.time()

    for epoca in range(1, epocas + 1):
        inicio_epoca: float = time.time()
        perda_c_acum: float = 0.0
        perda_g_acum: float = 0.0
        wasserstein_acum: float = 0.0
        total_lotes: int = 0

        for lote_real in carregador:
            lote_real = lote_real.to(dispositivo)
            tam: int = lote_real.size(0)
            total_lotes += 1

            # ---- Treinar Crítico (n_critico vezes por lote) ----
            for _ in range(n_critico):
                z: torch.Tensor = torch.randn(
                    tam, dimensao_latente, 1, 1, device=dispositivo
                )
                imagens_falsas: torch.Tensor = gerador(z)

                critico_real: torch.Tensor = critico(lote_real).mean()
                critico_falso: torch.Tensor = critico(
                    imagens_falsas.detach()
                ).mean()

                gp: torch.Tensor = calcular_penalidade_gradiente(
                    critico, lote_real, imagens_falsas, dispositivo
                )

                # Wasserstein loss + gradient penalty
                perda_c: torch.Tensor = (
                    critico_falso - critico_real + lambda_gp * gp
                )

                otimizador_c.zero_grad()
                perda_c.backward()
                otimizador_c.step()

            # ---- Treinar Gerador ----
            z = torch.randn(
                tam, dimensao_latente, 1, 1, device=dispositivo
            )
            imagens_falsas = gerador(z)
            perda_g: torch.Tensor = -critico(imagens_falsas).mean()

            otimizador_g.zero_grad()
            perda_g.backward()
            otimizador_g.step()

            perda_c_acum += perda_c.item()
            perda_g_acum += perda_g.item()
            wasserstein_acum += (critico_real - critico_falso).item()

        duracao: float = time.time() - inicio_epoca
        perda_c_media: float = perda_c_acum / total_lotes
        perda_g_media: float = perda_g_acum / total_lotes
        wasserstein_media: float = wasserstein_acum / total_lotes

        logger.info(
            "Época %03d/%03d | W-dist: %.4f | Perda C: %.4f | "
            "Perda G: %.4f | %.1fs",
            epoca,
            epocas,
            wasserstein_media,
            perda_c_media,
            perda_g_media,
            duracao,
        )

        # Salvar amostras visuais
        if epoca % intervalo_amostra == 0 or epoca == 1:
            with torch.no_grad():
                amostras: torch.Tensor = gerador(z_fixo)
                caminho_amostra: Path = (
                    dir_amostras / f"epoca_{epoca:04d}.png"
                )
                save_image(
                    amostras,
                    str(caminho_amostra),
                    nrow=4,
                    normalize=True,
                    value_range=(-1, 1),
                )
                logger.info("Amostra salva: %s", caminho_amostra)

        # Salvar checkpoint
        if epoca % intervalo_checkpoint == 0:
            salvar_checkpoint_gerador(
                gerador,
                dir_checkpoints / f"gerador_epoca_{epoca:04d}.pt",
                epoca,
                dimensao_latente,
            )

    # Salvar checkpoint final
    salvar_checkpoint_gerador(
        gerador,
        dir_checkpoints / "gerador_final.pt",
        epocas,
        dimensao_latente,
    )

    duracao_total: float = time.time() - inicio_total
    logger.info(
        "Treinamento concluído em %.1f min. Checkpoint final salvo.",
        duracao_total / 60,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Treinar WGAN-GP+SA para geração de imagens MEV",
    )
    parser.add_argument(
        "--dados",
        type=str,
        default="/app/armazenamento/reais",
        help="Diretório com imagens reais de MEV",
    )
    parser.add_argument(
        "--saida",
        type=str,
        default="/app/armazenamento",
        help="Diretório de saída para checkpoints e amostras",
    )
    parser.add_argument("--epocas", type=int, default=500)
    parser.add_argument("--lote", type=int, default=32)
    parser.add_argument("--latente", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--n-critico", type=int, default=5)
    parser.add_argument("--lambda-gp", type=float, default=10.0)
    parser.add_argument("--tamanho", type=int, default=256)

    args: argparse.Namespace = parser.parse_args()

    treinar_wgan_gp(
        diretorio_dados=Path(args.dados),
        diretorio_saida=Path(args.saida),
        epocas=args.epocas,
        tamanho_lote=args.lote,
        dimensao_latente=args.latente,
        lr=args.lr,
        n_critico=args.n_critico,
        lambda_gp=args.lambda_gp,
        tamanho_imagem=args.tamanho,
    )


if __name__ == "__main__":
    main()
