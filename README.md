# Nanoxus — Detecção de Fraude em Microscopia Eletrônica

Sistema de detecção de manipulação em imagens de microscopia eletrônica utilizando redes neurais convolucionais com Transfer Learning.

---

## Índice

- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Endpoints da API](#endpoints-da-api)
- [Fluxo de Uso Completo](#fluxo-de-uso-completo)
- [Pipeline de Machine Learning](#pipeline-de-machine-learning)
- [Gerador de Imagens Sintéticas](#gerador-de-imagens-sintéticas)
- [Configurações](#configurações)
- [Desenvolvimento](#desenvolvimento)
- [Solução de Problemas](#solução-de-problemas)

---

## Visão Geral

O Nanoxus classifica imagens de microscopia eletrônica em duas categorias:

| Classe        | Rótulo | Descrição                                           |
| ------------- | ------ | --------------------------------------------------- |
| **Real**      | 0      | Imagem genuína capturada por microscópio eletrônico |
| **Sintética** | 1      | Imagem manipulada, gerada ou adulterada             |

O sistema utiliza uma arquitetura de Transfer Learning baseada em ResNet18 (pré-treinada no ImageNet), com as camadas iniciais congeladas e um classificador binário customizado substituindo a camada final.

---

## Arquitetura do Sistema

```
┌─────────────────┐         ┌─────────────────┐
│  interface_web   │   :8080 │  api_nanoxus     │  :8000
│  (Vue.js + Vite) │ ──────► │  (FastAPI)       │
│                  │  proxy  │                  │
│  Node 20 Alpine  │  /api/* │  Python 3.11     │
└─────────────────┘         └────────┬─────────┘
                                     │
                            ┌────────▼─────────┐
                            │  Volume Docker    │
                            │  armazenamento_   │
                            │  modelos          │
                            │  ├── pesos/       │
                            │  │   ├── *.pt     │
                            │  │   └── *.json   │
                            │  ├── reais/       │
                            │  └── sinteticas/  │
                            └──────────────────┘
```

Os dois serviços rodam em containers Docker orquestrados pelo Docker Compose, conectados pela rede `rede_nanoxus`. O frontend faz proxy de todas as requisições `/api/*` para o backend. O container da API utiliza `runtime: nvidia` para aceleração GPU quando disponível.

---

## Estrutura de Diretórios

```
nanoxus/
├── docker-compose.yml
├── .gitignore
│
├── dados/
│   ├── reais/                    # Imagens reais de microscopia eletrônica
│   └── sinteticas/               # Imagens sintéticas geradas
│
├── scripts/
│   ├── gerar_sinteticas.py       # Gerador procedural de nanofios MEV
│   └── prompts.yaml              # Receitas YAML para geração
│
├── backend/
│   ├── Dockerfile                # CUDA 12.4 + Python 3.11
│   ├── requirements.txt          # PyTorch 2.7, FastAPI, OpenCV
│   │
│   ├── app/
│   │   ├── main.py               # Ponto de entrada, lifespan, CORS
│   │   ├── api/
│   │   │   └── router.py         # Agregador de rotas
│   │   └── core/
│   │       ├── config.py         # Settings (caminhos, env vars)
│   │       └── servidor.py       # Singleton ServidorAPI (carrega modelo)
│   │
│   ├── api/
│   │   └── rotas.py              # Endpoints: análise, treinamento
│   │
│   └── ml/
│       ├── modelo.py             # DetectorFraudeMEV (ResNet18/34, EfficientNet)
│       ├── processamento_dados.py # CarregadorDataset, ProcessadorImagem
│       └── treinador.py          # GerenciadorTreinamento, métricas, checkpoints
│
└── frontend/
    ├── Dockerfile                # Node 20 Alpine
    ├── package.json
    ├── vite.config.js            # Proxy /api → backend
    └── src/
        ├── main.ts               # Bootstrap Vue + PrimeVue + Router + Pinia
        ├── App.vue
        ├── router/
        ├── assets/main.css       # Tailwind + tema dark
        ├── composables/
        ├── components/
        ├── layouts/
        ├── services/
        ├── types/
        └── views/
            ├── DashboardView.vue
            ├── TreinamentoView.vue
            └── AnaliseView.vue
```

---

## Pré-requisitos

- **Docker** (versão 20.10+)
- **Docker Compose** (v2)
- **NVIDIA Container Toolkit** (para aceleração GPU — opcional)
- Pelo menos **4 GB de RAM** disponível
- Imagens reais em `dados/reais/` (formatos: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`)

```bash
docker --version
docker compose version
```

---

## Instalação e Execução

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd nanoxus
```

### 2. Verificar imagens do dataset

```bash
ls dados/reais/ | head -10
ls dados/reais/ | wc -l
```

### 3. Gerar imagens sintéticas (se necessário)

```bash
python scripts/gerar_sinteticas.py -n 1000
```

### 4. Construir e subir

```bash
docker compose build
docker compose up -d
```

### 5. Verificar

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "modelo_carregado": "True",
  "dispositivo": "cuda"
}
```

### 6. Interfaces

| Serviço                  | URL                         |
| ------------------------ | --------------------------- |
| **Frontend (Vue.js)**    | http://localhost:8080       |
| **API**                  | http://localhost:8000       |
| **Documentação Swagger** | http://localhost:8000/docs  |
| **Documentação ReDoc**   | http://localhost:8000/redoc |

---

## Endpoints da API

### `GET /health`

Health check do sistema.

```bash
curl http://localhost:8000/health
```

### `GET /api/status`

Status do serviço.

```bash
curl http://localhost:8000/api/status
```

### `POST /api/analisar-imagem`

Envia uma imagem para classificação.

```bash
curl -X POST http://localhost:8000/api/analisar-imagem \
  -F "arquivo=@caminho/para/imagem.png"
```

Resposta:

```json
{
  "probabilidade_fraude": 0.12345,
  "classe_predita": "Real",
  "tempo_inferencia_ms": 26.97,
  "nome_arquivo": "imagem.png",
  "dimensoes_originais": [1024, 768]
}
```

| Campo                  | Descrição                                   |
| ---------------------- | ------------------------------------------- |
| `probabilidade_fraude` | Valor entre 0 e 1. Acima de 0.5 = Sintética |
| `classe_predita`       | "Real" ou "Sintética"                       |
| `tempo_inferencia_ms`  | Tempo de inferência em milissegundos        |
| `nome_arquivo`         | Nome do arquivo enviado                     |
| `dimensoes_originais`  | Largura e altura originais da imagem        |

### `POST /api/iniciar-treinamento`

Dispara o treinamento em background.

```bash
curl -X POST http://localhost:8000/api/iniciar-treinamento \
  -H "Content-Type: application/json" \
  -d '{
    "epochs": 30,
    "batch_size": 32,
    "learning_rate": 0.0001,
    "arquitetura": "resnet18",
    "use_mock": false,
    "early_stop_patience": 10
  }'
```

Parâmetros (todos opcionais, valores padrão mostrados acima):

| Parâmetro             | Tipo   | Descrição                                              |
| --------------------- | ------ | ------------------------------------------------------ |
| `epochs`              | int    | Número máximo de épocas de treinamento                 |
| `batch_size`          | int    | Tamanho do lote (batch size)                           |
| `learning_rate`       | float  | Learning rate inicial para o AdamW                     |
| `arquitetura`         | string | `"resnet18"`, `"resnet34"` ou `"efficientnet_b0"`      |
| `use_mock`            | bool   | Se `true`, gera dados sintéticos aleatórios para teste |
| `early_stop_patience` | int    | Épocas sem melhora antes de parar                      |

Resposta:

```json
{
  "id_tarefa": "b7172668f9b9",
  "mensagem": "Treinamento iniciado em background",
  "data_inicio": "2026-02-17 01:55:10"
}
```

### `GET /api/treinamento/{id_tarefa}`

Consulta o estado de uma tarefa de treinamento.

```bash
curl http://localhost:8000/api/treinamento/b7172668f9b9
```

Estados possíveis: `enfileirado` → `em_execucao` → `concluido` ou `erro`.

Quando concluído, o campo `resultado` contém as métricas completas:

```json
{
  "estado": "concluido",
  "resultado": {
    "melhor_acuracia_validacao": 0.95,
    "melhor_epoca": 12,
    "total_epocas": 30,
    "epocas": [
      {
        "epoca": 1,
        "perda_treino": 0.6923,
        "acuracia_treino": 0.52,
        "perda_validacao": 0.6801,
        "acuracia_validacao": 0.58,
        "duracao_segundos": 45.2,
        "learning_rate": 0.0001
      }
    ]
  }
}
```

---

## Fluxo de Uso Completo

### Cenário 1: Teste rápido com dados mock

```bash
docker compose up -d

curl -X POST http://localhost:8000/api/iniciar-treinamento \
  -H "Content-Type: application/json" \
  -d '{"epochs": 3, "batch_size": 4, "use_mock": true}'

# Acompanhar (substituir o ID retornado)
curl http://localhost:8000/api/treinamento/<id_tarefa>

# Testar inferência
curl -X POST http://localhost:8000/api/analisar-imagem \
  -F "arquivo=@qualquer_imagem.png"
```

### Cenário 2: Treinamento completo

```bash
# Gerar sintéticas (se ainda não existem)
python scripts/gerar_sinteticas.py -n 1000

docker compose up -d

curl -X POST http://localhost:8000/api/iniciar-treinamento \
  -H "Content-Type: application/json" \
  -d '{
    "epochs": 50,
    "batch_size": 32,
    "learning_rate": 0.0001,
    "arquitetura": "resnet18",
    "early_stop_patience": 10
  }'

# Monitorar
watch -n 10 'curl -s http://localhost:8000/api/treinamento/<id_tarefa> | python3 -m json.tool'
```

Ao concluir, o modelo é recarregado automaticamente na memória.

---

## Pipeline de Machine Learning

### Pré-processamento (`ProcessadorImagem`)

1. **Conversão de canais** — Grayscale, BGRA ou BGR → RGB
2. **Remoção de ruído** — Non-local Means Denoising (OpenCV)
3. **Redimensionamento** — 224×224 pixels
4. **Normalização** — Mean/Std do ImageNet (`[0.485, 0.456, 0.406]` / `[0.229, 0.224, 0.225]`)
5. **Conversão para tensor** — `torch.Tensor` com dimensão de batch

### Data Augmentation (treinamento)

- Flip horizontal (p=0.5)
- Flip vertical (p=0.3)
- Rotação aleatória (±15°)
- Color Jitter (brilho ±0.2, contraste ±0.2)

### Arquitetura do Modelo (`DetectorFraudeMEV`)

```
ResNet18 (pré-treinada ImageNet)
├── Camadas convolucionais [CONGELADAS]
├── Camadas finais [DESCONGELADAS para fine-tuning]
└── Classificador customizado:
    ├── Linear(512, 256) → BatchNorm → ReLU → Dropout(0.4)
    ├── Linear(256, 64)  → BatchNorm → ReLU → Dropout(0.2)
    └── Linear(64, 1)    → Sigmoid (na inferência)
```

Arquiteturas disponíveis: `resnet18`, `resnet34`, `efficientnet_b0`.

### Treinamento (`GerenciadorTreinamento`)

- **Otimizador**: AdamW (weight decay = 1e-4)
- **Loss**: BCEWithLogitsLoss
- **Scheduler**: Cosine Annealing (LR mínimo = 1e-6)
- **Gradient clipping**: max_norm = 1.0
- **Early stopping**: Configurável (padrão 10 épocas)
- **Split**: 80% treino / 20% validação (seed fixa = 42)
- **Checkpoints** salvos em `/app/armazenamento/pesos/`:
  - `detector_mev_YYYYMMDD_HHMMSS_melhor.pt`
  - `detector_mev_YYYYMMDD_HHMMSS_final.pt`
  - `historico_YYYYMMDD_HHMMSS.json`

---

## Gerador de Imagens Sintéticas

O script `scripts/gerar_sinteticas.py` gera micrografias procedurais de nanofios MEV controladas por receitas YAML.

```bash
python scripts/gerar_sinteticas.py                        # usa prompts.yaml
python scripts/gerar_sinteticas.py -p meu_prompt.yaml     # prompt custom
python scripts/gerar_sinteticas.py -n 500 --seed 99       # flags opcionais
```

### Receitas disponíveis (`scripts/prompts.yaml`)

| Receita           | Descrição                                             |
| ----------------- | ----------------------------------------------------- |
| `dispersos_finos` | Poucos nanofios finos isolados sobre substrato liso   |
| `alinhados_denso` | Nanofios paralelos (crescimento epitaxial)            |
| `rede_cruzada`    | Nanofios cruzados formando malha                      |
| `grossos_curtos`  | Alta magnificação, nanofios grossos, substrato poroso |
| `clusters`        | Aglomerados emanando de pontos catalíticos            |
| `ruidoso`         | Baixo contraste, alto ruído (imagens difíceis)        |
| `floresta_top`    | Vista de topo — pontas circulares sobre fundo escuro  |

Para criar novas receitas, edite `scripts/prompts.yaml`.

---

## Configurações

| Variável                | Padrão                        | Descrição                      |
| ----------------------- | ----------------------------- | ------------------------------ |
| `APP_NAME`              | Nanoxus                       | Nome da aplicação              |
| `DEBUG`                 | True                          | Modo debug                     |
| `ARMAZENAMENTO_PATH`    | /app/armazenamento            | Raiz do volume de persistência |
| `DADOS_REAIS_PATH`      | /app/armazenamento/reais      | Caminho das imagens reais      |
| `DADOS_SINTETICAS_PATH` | /app/armazenamento/sinteticas | Caminho das imagens sintéticas |
| `MODELO_PESOS_PATH`     | /app/armazenamento/pesos      | Caminho dos checkpoints        |

---

## Desenvolvimento

### Logs

```bash
docker compose logs -f api_nanoxus
docker compose logs -f interface_web
```

### Shell do container

```bash
docker exec -it api_nanoxus bash
docker exec -it interface_web sh
```

### Verificar artefatos

```bash
docker exec api_nanoxus ls -lh /app/armazenamento/pesos/
```

### Rebuild

O código é montado via volume bind-mount (hot-reload). Para alterações em `Dockerfile`, `requirements.txt` ou `package.json`:

```bash
docker compose up --build
```

### Parar

```bash
docker compose down        # mantém volumes
docker compose down -v     # remove volumes (pesos treinados)
```

---

## Solução de Problemas

| Problema                           | Solução                                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `ModuleNotFoundError` no container | Verificar volume: `docker exec api_nanoxus ls /app/ml/`                                                            |
| Build lento na primeira vez        | Normal — PyTorch ~800MB. Builds seguintes usam cache                                                               |
| `FileNotFoundError` no treinamento | Imagens devem estar em `dados/reais/` e/ou `dados/sinteticas/`. Use `use_mock: true` para testar                   |
| Porta 8000 ou 8080 em uso          | Alterar mapeamento no `docker-compose.yml` (ex: `"8001:8000"`)                                                     |
| Memória insuficiente               | Reduzir `batch_size` no treinamento (ex: 8 ou 16)                                                                  |
| Container reiniciando em loop      | Verificar logs: `docker compose logs api_nanoxus`                                                                  |
| GPU não detectada                  | Verificar NVIDIA Container Toolkit: `docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi` |

---

## Stack Tecnológica

| Componente              | Tecnologia            | Versão       |
| ----------------------- | --------------------- | ------------ |
| Backend                 | Python + FastAPI      | 3.11 / 0.115 |
| Frontend                | Vue.js 3 + Vite       | 3.5 / 6.0    |
| Deep Learning           | PyTorch + TorchVision | 2.7 / 0.22   |
| Processamento de Imagem | OpenCV + Pillow       | 4.10 / 11.1  |
| Containerização         | Docker + Compose      | v2           |
| GPU                     | NVIDIA CUDA           | 12.4         |
| UI                      | PrimeVue + Tailwind   | 4.3 / 4.0    |

---
