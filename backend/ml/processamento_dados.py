from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms


class DatasetMicroscopia(Dataset):

    def __init__(
        self,
        lista_caminhos: list[Path],
        lista_rotulos: list[int],
        transformacao_composta: Optional[transforms.Compose] = None,
    ) -> None:
        self.lista_caminhos: list[Path] = lista_caminhos
        self.lista_rotulos: list[int] = lista_rotulos
        self.transformacao_composta: Optional[transforms.Compose] = transformacao_composta

    def __len__(self) -> int:
        return len(self.lista_caminhos)

    def __getitem__(self, indice: int) -> tuple[torch.Tensor, int]:
        caminho_imagem: Path = self.lista_caminhos[indice]
        rotulo: int = self.lista_rotulos[indice]

        imagem: Image.Image = Image.open(caminho_imagem).convert("RGB")

        if self.transformacao_composta is not None:
            tensor_imagem: torch.Tensor = self.transformacao_composta(imagem)
        else:
            tensor_imagem = transforms.ToTensor()(imagem)

        return tensor_imagem, rotulo


class CarregadorDataset:

    EXTENSOES_VALIDAS: set[str] = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

    def __init__(
        self,
        caminho_reais: Path | str,
        caminho_sinteticas: Path | str,
        tamanho_imagem: int = 224,
        tamanho_lote: int = 32,
        proporcao_treino: float = 0.8,
        semente_aleatoria: int = 42,
    ) -> None:
        self.caminho_reais: Path = Path(caminho_reais)
        self.caminho_sinteticas: Path = Path(caminho_sinteticas)
        self.tamanho_imagem: int = tamanho_imagem
        self.tamanho_lote: int = tamanho_lote
        self.proporcao_treino: float = proporcao_treino
        self.semente_aleatoria: int = semente_aleatoria
        self.transformacao_composta: Optional[transforms.Compose] = None

    def preparar_transformacoes(self, modo_treino: bool = True) -> transforms.Compose:
        lista_transformacoes: list = [
            transforms.Resize((self.tamanho_imagem, self.tamanho_imagem)),
        ]

        if modo_treino:
            lista_transformacoes.extend([
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomVerticalFlip(p=0.3),
                transforms.RandomRotation(degrees=15),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
            ])

        lista_transformacoes.extend([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        self.transformacao_composta = transforms.Compose(lista_transformacoes)
        return self.transformacao_composta

    def _listar_imagens(self, caminho_diretorio: Path) -> list[Path]:
        lista_arquivos: list[Path] = []

        if not caminho_diretorio.exists():
            return lista_arquivos

        for arquivo in sorted(caminho_diretorio.iterdir()):
            if arquivo.is_file() and arquivo.suffix.lower() in self.EXTENSOES_VALIDAS:
                lista_arquivos.append(arquivo)

        return lista_arquivos

    def _construir_listas(self) -> tuple[list[Path], list[int]]:
        caminhos: list[Path] = []
        rotulos: list[int] = []

        imagens_reais: list[Path] = self._listar_imagens(self.caminho_reais)
        for caminho_imagem in imagens_reais:
            caminhos.append(caminho_imagem)
            rotulos.append(0)

        imagens_sinteticas: list[Path] = self._listar_imagens(self.caminho_sinteticas)
        for caminho_imagem in imagens_sinteticas:
            caminhos.append(caminho_imagem)
            rotulos.append(1)

        return caminhos, rotulos

    def _gerar_mock(self, quantidade: int = 20) -> tuple[list[Path], list[int]]:
        diretorio_mock: Path = Path("/tmp/nanoxus_mock")
        diretorio_reais_mock: Path = diretorio_mock / "reais"
        diretorio_sinteticas_mock: Path = diretorio_mock / "sinteticas"
        diretorio_reais_mock.mkdir(parents=True, exist_ok=True)
        diretorio_sinteticas_mock.mkdir(parents=True, exist_ok=True)

        caminhos: list[Path] = []
        rotulos: list[int] = []

        for i in range(quantidade):
            matriz_pixels: np.ndarray = np.random.randint(
                0, 255, (self.tamanho_imagem, self.tamanho_imagem, 3), dtype=np.uint8
            )
            imagem_mock: Image.Image = Image.fromarray(matriz_pixels)

            if i < quantidade // 2:
                caminho_arquivo: Path = diretorio_reais_mock / f"mock_real_{i:04d}.png"
                imagem_mock.save(caminho_arquivo)
                caminhos.append(caminho_arquivo)
                rotulos.append(0)
            else:
                caminho_arquivo = diretorio_sinteticas_mock / f"mock_sintetica_{i:04d}.png"
                imagem_mock.save(caminho_arquivo)
                caminhos.append(caminho_arquivo)
                rotulos.append(1)

        return caminhos, rotulos

    def carregar_imagens(
        self, usar_mock: bool = False
    ) -> tuple[DataLoader, DataLoader]:
        if self.transformacao_composta is None:
            self.preparar_transformacoes(modo_treino=True)

        if usar_mock:
            lista_caminhos, lista_rotulos = self._gerar_mock()
        else:
            lista_caminhos, lista_rotulos = self._construir_listas()

        if len(lista_caminhos) == 0:
            raise FileNotFoundError(
                f"Nenhuma imagem encontrada nos diretórios: "
                f"{self.caminho_reais}, {self.caminho_sinteticas}. "
                f"Use usar_mock=True para gerar dados sintéticos de teste."
            )

        dataset_completo: DatasetMicroscopia = DatasetMicroscopia(
            lista_caminhos=lista_caminhos,
            lista_rotulos=lista_rotulos,
            transformacao_composta=self.transformacao_composta,
        )

        total_amostras: int = len(dataset_completo)
        quantidade_treino: int = int(total_amostras * self.proporcao_treino)
        quantidade_validacao: int = total_amostras - quantidade_treino

        gerador: torch.Generator = torch.Generator().manual_seed(self.semente_aleatoria)

        dataset_treino: Dataset
        dataset_validacao: Dataset
        dataset_treino, dataset_validacao = random_split(
            dataset_completo,
            [quantidade_treino, quantidade_validacao],
            generator=gerador,
        )

        carregador_treino: DataLoader = DataLoader(
            dataset_treino,
            batch_size=self.tamanho_lote,
            shuffle=True,
            num_workers=os.cpu_count() or 2,
            pin_memory=torch.cuda.is_available(),
            drop_last=True,
        )

        carregador_validacao: DataLoader = DataLoader(
            dataset_validacao,
            batch_size=self.tamanho_lote,
            shuffle=False,
            num_workers=os.cpu_count() or 2,
            pin_memory=torch.cuda.is_available(),
            drop_last=False,
        )

        return carregador_treino, carregador_validacao

    def resumo(self) -> dict[str, int]:
        imagens_reais: list[Path] = self._listar_imagens(self.caminho_reais)
        imagens_sinteticas: list[Path] = self._listar_imagens(self.caminho_sinteticas)
        total: int = len(imagens_reais) + len(imagens_sinteticas)
        quantidade_treino: int = int(total * self.proporcao_treino)
        quantidade_validacao: int = total - quantidade_treino

        return {
            "total_reais": len(imagens_reais),
            "total_sinteticas": len(imagens_sinteticas),
            "total_amostras": total,
            "amostras_treino": quantidade_treino,
            "amostras_validacao": quantidade_validacao,
            "tamanho_lote": self.tamanho_lote,
        }


class ProcessadorImagem:

    MEDIA_IMAGENET: list[float] = [0.485, 0.456, 0.406]
    DESVIO_IMAGENET: list[float] = [0.229, 0.224, 0.225]

    @staticmethod
    def converter_para_rgb(imagem_entrada: np.ndarray) -> np.ndarray:
        numero_dimensoes: int = len(imagem_entrada.shape)

        if numero_dimensoes == 2:
            imagem_rgb: np.ndarray = cv2.cvtColor(imagem_entrada, cv2.COLOR_GRAY2RGB)
            return imagem_rgb

        numero_canais: int = imagem_entrada.shape[2]

        if numero_canais == 4:
            imagem_rgb = cv2.cvtColor(imagem_entrada, cv2.COLOR_BGRA2RGB)
            return imagem_rgb

        if numero_canais == 3:
            imagem_rgb = cv2.cvtColor(imagem_entrada, cv2.COLOR_BGR2RGB)
            return imagem_rgb

        return imagem_entrada

    @staticmethod
    def remover_ruido(
        imagem_entrada: np.ndarray,
        intensidade_filtro: int = 10,
        tamanho_janela_busca: int = 21,
        tamanho_janela_template: int = 7,
    ) -> np.ndarray:
        imagem_limpa: np.ndarray = cv2.fastNlMeansDenoisingColored(
            imagem_entrada,
            None,
            intensidade_filtro,
            intensidade_filtro,
            tamanho_janela_template,
            tamanho_janela_busca,
        )
        return imagem_limpa

    @staticmethod
    def equalizar_histograma(imagem_entrada: np.ndarray) -> np.ndarray:
        imagem_lab: np.ndarray = cv2.cvtColor(imagem_entrada, cv2.COLOR_RGB2LAB)
        canal_l: np.ndarray
        canal_a: np.ndarray
        canal_b: np.ndarray
        canal_l, canal_a, canal_b = cv2.split(imagem_lab)

        clahe: cv2.CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        canal_l_equalizado: np.ndarray = clahe.apply(canal_l)

        imagem_lab_equalizada: np.ndarray = cv2.merge(
            [canal_l_equalizado, canal_a, canal_b]
        )
        imagem_resultado: np.ndarray = cv2.cvtColor(
            imagem_lab_equalizada, cv2.COLOR_LAB2RGB
        )
        return imagem_resultado

    @staticmethod
    def normalizar_para_tensor(
        imagem_entrada: np.ndarray, tamanho_alvo: int = 224
    ) -> torch.Tensor:
        imagem_pil: Image.Image = Image.fromarray(imagem_entrada)

        transformacao_inferencia: transforms.Compose = transforms.Compose([
            transforms.Resize((tamanho_alvo, tamanho_alvo)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=ProcessadorImagem.MEDIA_IMAGENET,
                std=ProcessadorImagem.DESVIO_IMAGENET,
            ),
        ])

        tensor_saida: torch.Tensor = transformacao_inferencia(imagem_pil)
        return tensor_saida

    @classmethod
    def pipeline_preprocessamento(
        cls,
        caminho_imagem: Path | str,
        tamanho_alvo: int = 224,
        aplicar_denoising: bool = True,
        aplicar_equalizacao: bool = False,
    ) -> torch.Tensor:
        caminho: Path = Path(caminho_imagem)

        if not caminho.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {caminho}")

        imagem_bruta: np.ndarray = cv2.imread(str(caminho), cv2.IMREAD_UNCHANGED)

        if imagem_bruta is None:
            raise ValueError(f"Não foi possível decodificar a imagem: {caminho}")

        imagem_rgb: np.ndarray = cls.converter_para_rgb(imagem_bruta)

        if aplicar_denoising:
            imagem_rgb = cls.remover_ruido(imagem_rgb)

        if aplicar_equalizacao:
            imagem_rgb = cls.equalizar_histograma(imagem_rgb)

        tensor_final: torch.Tensor = cls.normalizar_para_tensor(
            imagem_rgb, tamanho_alvo
        )

        tensor_final = tensor_final.unsqueeze(0)

        return tensor_final
