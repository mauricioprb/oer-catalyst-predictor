# Nanoxus - Predição de Atividade OER via CHGNet

Plataforma para predição da atividade eletrocatalítica na **Reação de Evolução de Oxigênio (OER - Oxygen Evolution Reaction)** a partir de estruturas cristalinas de óxidos de metais de transição.

O sistema utiliza o **CHGNet** (Crystal Hamiltonian Graph Neural Network) - um potencial interatômico universal de aprendizado de máquina com ~412 mil parâmetros, pré-treinado em ~1,6 milhão de estruturas do [Materials Project](https://materialsproject.org/) - combinado com o framework **CHE** (Computational Hydrogen Electrode) de Nørskov et al. para calcular o overpotential teórico de catalisadores OER sem a necessidade de simulações DFT completas.

---

## Índice

- [O que é a OER?](#o-que-é-a-oer)
- [O que o sistema prediz?](#o-que-o-sistema-prediz)
- [Pipeline Científico - CHGNet + CHE](#pipeline-científico--chgnet--che)
- [Arquitetura](#arquitetura)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Endpoints da API](#endpoints-da-api)
- [Fluxo de Uso](#fluxo-de-uso)
- [Desenvolvimento](#desenvolvimento)
- [Solução de Problemas](#solução-de-problemas)
- [Stack](#stack)
- [Referências](#referências)

---

## O que é a OER?

A **Reação de Evolução de Oxigênio (OER)** é a semirreação anódica em dispositivos de eletrólise da água e baterias metal-ar:

$$2\text{H}_2\text{O} \rightarrow \text{O}_2 + 4\text{H}^+ + 4e^-$$

A OER é o gargalo cinético na produção de hidrogênio verde por eletrólise, exigindo catalisadores eficientes para reduzir o **overpotential** (a tensão extra necessária além do potencial termodinâmico reversível de 1,23 V). Encontrar catalisadores com baixo overpotential é essencial para tornar a eletrólise economicamente viável.

### Por que usar machine learning?

O método tradicional para avaliar catalisadores OER requer simulações DFT (Density Functional Theory) de alto custo computacional - cada estrutura pode levar horas ou dias de cálculo em clusters HPC. O CHGNet substitui essas simulações com inferência em segundos/minutos via GPU, mantendo precisão competitiva para triagem de materiais (*screening*).

---

## O que o sistema prediz?

O Nanoxus recebe um arquivo de estrutura cristalina (`.cif`, `.xyz` ou `.vasp`) contendo um óxido de metal de transição e retorna:

| Propriedade              | Descrição                                                                  |
| ------------------------ | -------------------------------------------------------------------------- |
| **Overpotential (η)**    | Overpotential teórico OER em volts - quanto menor, melhor o catalisador    |
| **Viabilidade**          | `Viável` se η < 0,40 V (indicador de catalisador promissor)               |
| **Band gap**             | Band gap estimado em eV (indica se o material é condutor, semicondutor ou isolante) |
| **ΔG\*OH**               | Energia livre de Gibbs de adsorção do intermediário \*OH (eV)              |
| **ΔG\*O**                | Energia livre de Gibbs de adsorção do intermediário \*O (eV)               |
| **ΔG\*OOH**              | Energia livre de Gibbs de adsorção do intermediário \*OOH (eV)             |

### Como interpretar os resultados

- **η < 0,40 V** → catalisador **viável** e promissor para aplicação
- **η = 0,00 V** → catalisador ideal (termodinamicamente perfeito, teórico)
- **η > 0,40 V** → catalisador **ineficiente** - requer muita energia extra
- **ΔG\*OH ≈ 1,60 eV** → pico do Gráfico de dispersão OER - atividade máxima segundo as relações de escala universais

O frontend apresenta um gráfico de dispersão que posiciona o material analisado no gráfico de atividade OER (overpotential vs. ΔG\*OH), permitindo comparação visual com catalisadores de referência.

---

## Pipeline Científico - CHGNet + CHE

O pipeline de predição OER combina o CHGNet como motor de inferência com o framework do Computational Hydrogen Electrode (CHE) de Nørskov et al.:

### Etapa 1 - Parsing e validação da estrutura

O arquivo enviado é interpretado como CIF, XYZ ou VASP via [`pymatgen.core.Structure`](https://pymatgen.org/). A composição química é validada: o material **deve conter oxigênio (O)** e **pelo menos um metal de transição** (Sc–Zn, Y–Cd, La–Hg, Ac). Estruturas sem esses elementos são rejeitadas com erro 422.

### Etapa 2 - Predição bulk (CHGNet)

O CHGNet recebe a estrutura cristalina completa e prediz via uma única passagem forward na GNN:

| Propriedade                 | Uso no pipeline                                        |
| --------------------------- | ------------------------------------------------------ |
| Energia por átomo (eV/at)   | Referência energética para cálculo de γ de superfície  |
| Forças atômicas (eV/Å)      | Guiam a relaxação do slab                              |
| Tensor de stress (GPa)      | Informação estrutural                                  |
| Momentos magnéticos (μ_B)   | Correção da energia de adsorção + estimativa de band gap |

O momento magnético médio dos metais de transição (μ_metal) reflete a configuração eletrônica d e influencia diretamente a reatividade da superfície.

### Etapa 3 - Geração e relaxação de slab

Para calcular a energia de superfície, o sistema gera slabs (fatias do cristal com vácuo):

1. **`pymatgen.SlabGenerator`** gera slabs para 5 orientações cristalográficas: (110), (100), (001), (101), (111)
2. **Seleção de slab**: prioriza slabs simétricos (terminações equivalentes), depois não-polares
3. **Condição de contorno**: a metade inferior dos átomos é fixada (`ASE FixAtoms`), simulando o bulk
4. **Relaxação**: o slab é relaxado com o otimizador `ASE BFGS` usando o CHGNet como calculadora interatômica ($f_{max}$ = 0,05 eV/Å, máx. 80 passos)
5. **Energia de superfície**:

$$\gamma = \frac{E_{slab} - N \cdot e_{bulk}}{2A} \times 16,0218 \quad [\text{J/m}^2]$$

onde $E_{slab}$ é a energia total do slab relaxado, $N$ é o número de átomos, $e_{bulk}$ é a energia por átomo do bulk e $A$ é a área da superfície.

### Etapa 4 - Energias de adsorção dos intermediários OER

As energias de adsorção são calculadas usando **relações de escala universais** (Man et al., *ChemCatChem* 2011), calibradas por metal de transição:

1. **ΔG\*OH (baseline)**: valor tabelado para cada metal de transição, selecionando o metal com ΔG\*OH mais próximo do pico do Gráfico de dispersão (~1,60 eV)

2. **Correções físicas** aplicadas ao baseline (limitadas a ±0,30 eV):
   - **Energia de superfície**: $\Delta\gamma = \gamma - \gamma_{ref}$ → superfícies mais reativas (γ↑) reduzem ΔG\*OH
   - **Momento magnético**: $\Delta\mu = 0,02 \times (\mu_{metal} - 1,0)$ → reflete o estado eletrônico d

3. **Relações de escala** para os demais intermediários:
   - $\Delta G_{*O} = 2 \times \Delta G_{*OH}$
   - $\Delta G_{*OOH} = \Delta G_{*OH} + 3,20 \text{ eV}$

Essas relações lineares são fundamentadas na correlação termodinâmica entre as energias de ligação dos intermediários oxigenados em superfícies de óxidos.

### Etapa 5 - Cálculo do overpotential teórico

O mecanismo OER de 4 elétrons no framework CHE define 4 etapas elementares:

$$
\begin{aligned}
\Delta G_1 &= \Delta G_{*OH} \\
\Delta G_2 &= \Delta G_{*O} - \Delta G_{*OH} \\
\Delta G_3 &= \Delta G_{*OOH} - \Delta G_{*O} \\
\Delta G_4 &= 4 \times 1,23 - \Delta G_{*OOH}
\end{aligned}
$$

O **overpotential teórico** é determinado pela etapa limitante:

$$\eta = \max(\Delta G_1, \Delta G_2, \Delta G_3, \Delta G_4) - 1,23 \text{ V}$$

O material é considerado **viável** se $\eta < 0,40$ V - limiar amplamente utilizado na literatura como indicador de catalisadores promissores para OER.

### Etapa 6 - Estimativa de band gap

O band gap é estimado a partir dos momentos magnéticos e da energia bulk, categorizando o material:

| Categoria                          | Critério           | Band gap estimado |
| ---------------------------------- | ------------------ | ----------------- |
| Metais d⁰ (Sc, Ti, Zr, Hf, etc.) | Todos metais ∈ d⁰  | 2,5 – 5,0 eV     |
| Alto momento magnético             | μ > 2,0 μ_B        | 1,5 – 4,5 eV     |
| Baixo momento magnético            | μ < 0,5 μ_B        | 0,0 – 1,0 eV     |
| Intermediário                      | 0,5 ≤ μ ≤ 2,0 μ_B  | 0,5 – 3,0 eV     |

Essa estimativa é útil para triagem rápida, indicando se o material tem caráter metálico (gap ~0), semicondutor ou isolante.

---

## Arquitetura

```
┌─────────────────┐           ┌─────────────────┐
│ interface_web   │   :8080   │ api_nanoxus     │ :8000
│ (Vue.js + Vite) │──────────►│ (FastAPI)       │
│                 │  proxy    │                 │
│ Node 20 Alpine  │  /api/*   │ Python 3.11     │
│                 │  /health  │ CUDA 12.4       │
└─────────────────┘           └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ CHGNet (GNN)    │
                              │ ~412k params    │
                              │ GPU (CUDA)      │
                              │                 │
                              │ pymatgen + ASE  │
                              │ SlabGenerator   │
                              │ BFGS relaxation │
                              └─────────────────┘
```

- **Frontend (Vue.js 3 + Vite)** - Interface web para upload de estruturas cristalinas, visualização 3D interativa (3Dmol.js), exibição de métricas OER, Gráfico de dispersão plot e tema claro/escuro
- **Backend (FastAPI + CHGNet)** - API REST que recebe arquivos de estrutura, executa o pipeline de predição OER e retorna os resultados
- **CHGNet** - Rede neural em grafo que substitui cálculos DFT, inferindo energia, forças, stress e momentos magnéticos
- **Docker Compose** - Orquestra os dois serviços na rede `rede_nanoxus`. O Vite faz proxy de `/api/*` e `/health` para o backend. O container da API utiliza `runtime: nvidia` para aceleração GPU

---

## Estrutura de Diretórios

```
oer-catalyst-predictor/
├── docker-compose.yml                  # Orquestração dos containers
├── package.json                        # Scripts raiz (lint)
│
├── backend/
│   ├── Dockerfile                      # CUDA 12.4 + Python 3.11
│   ├── requirements.txt                # PyTorch 2.10, FastAPI, pymatgen, CHGNet, ASE
│   └── app/
│       ├── __init__.py
│       ├── main.py                     # Ponto de entrada FastAPI, CORS, routers
│       ├── api/
│       │   ├── __init__.py
│       │   ├── schemas.py              # Pydantic: PredictionResponse, AdsorptionEnergies
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── health.py           # GET /health - status do preditor
│       │       └── prediction.py       # POST /api/predict - predição OER
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py               # Configurações, extensões permitidas, CORS
│       │   └── lifespan.py             # Carregamento do CHGNet no startup
│       └── domain/
│           ├── __init__.py
│           ├── constants.py            # Constantes OER: E_rev, limiar η, ΔG*OH por metal
│           ├── exceptions.py           # CIFParsingError, InvalidCatalystError
│           └── services/
│               ├── __init__.py
│               └── oer_predictor.py    # OERPredictor - pipeline CHGNet + CHE completo
│
└── frontend/
    ├── Dockerfile                      # Node 20 Alpine
    ├── package.json                    # Vue 3, PrimeVue, Tailwind 4, 3Dmol, Chart.js
    ├── vite.config.js                  # Proxy /api e /health → backend
    ├── index.html
    └── src/
        ├── main.ts                     # Bootstrap Vue + PrimeVue + Router + Pinia
        ├── App.vue                     # Root - <router-view> + Toast
        ├── assets/
        │   └── main.css                # Tailwind + tema customizado
        ├── router/
        │   └── index.ts                # Rota única: /predicao
        ├── layouts/
        │   └── DashboardLayout.vue     # Header, status da API, tema
        ├── views/
        │   └── PredicaoView.vue        # Página principal - upload, 3D, resultados, Gráfico de dispersão
        ├── components/
        │   ├── predicao/
        │   │   ├── AdsorptionEnergies.vue   # Energias ΔG*OH, ΔG*O, ΔG*OOH
        │   │   ├── FileUploader.vue         # Upload de .cif/.xyz/.vasp
        │   │   ├── InferenceDetails.vue     # Tempo de inferência, fórmula
        │   │   ├── MoleculeViewer.vue       # Visualizador 3D (3Dmol.js)
        │   │   ├── OERMetrics.vue           # Cards de overpotential, viabilidade, band gap
        │   │   ├── OverpotentialGauge.vue   # Gauge visual do overpotential
        │   │   └── VolcanoPlot.vue          # Gráfico Gráfico de dispersão (η vs ΔG*OH)
        │   └── ui/
        │       ├── MetricCard.vue           # Card genérico de métrica
        │       ├── PageHeader.vue           # Cabeçalho de página
        │       └── StatusIndicator.vue      # Indicador online/offline da API
        ├── composables/
        │   ├── useFileReader.ts        # Leitura de arquivo para visualização 3D
        │   ├── useHealthCheck.ts       # Polling de /health (15s)
        │   ├── useOERPrediction.ts     # Lógica de predição OER
        │   └── useTheme.ts             # Tema claro/escuro
        ├── services/
        │   └── api.ts                  # apiService: verificarSaude(), predizirOER()
        ├── stores/
        │   └── health.ts               # Pinia store - estado da API
        ├── types/
        │   ├── index.ts                # Barrel export
        │   ├── api.ts                  # StatusSaude, EnergiaAdsorcao, RespostaOER
        │   └── navigation.ts           # ItemNavegacao, ITENS_NAVEGACAO
        └── utils/
            └── format.ts               # Formatação de valores numéricos
```

---

## Pré-requisitos

- **Docker** (versão 20.10+)
- **Docker Compose**
- **NVIDIA Container Toolkit** (para aceleração GPU - recomendado)
- Pelo menos **8 GB de RAM** disponível (CHGNet + PyTorch)

```bash
docker --version
docker compose version
```

> **Nota**: sem GPU, o CHGNet executa em CPU - a predição funciona, porém é significativamente mais lenta.

---

## Instalação e Execução

### 1. Clonar o repositório

```bash
git clone git@github.com:mauricioprb/oer-catalyst-predictor.git
cd oer-catalyst-predictor
```

### 2. Construir e subir

```bash
docker compose build
docker compose up -d
```

O primeiro build pode levar alguns minutos (PyTorch + CHGNet + pymatgen ~2 GB). Builds subsequentes usam cache do Docker.

### 3. Verificar se o preditor carregou

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "predictor_loaded": true
}
```

> O CHGNet leva alguns segundos para carregar na inicialização. Enquanto `predictor_loaded` for `false`, a API retornará 503 nas requisições de predição.

### 4. Acessar

| Serviço                  | URL                         |
| ------------------------ | --------------------------- |
| **Frontend (Vue.js)**    | http://localhost:8080        |
| **API**                  | http://localhost:8000        |
| **Documentação Swagger** | http://localhost:8000/docs   |
| **Documentação ReDoc**   | http://localhost:8000/redoc  |

---

## Endpoints da API

### `GET /health`

Health check do sistema. Retorna se o preditor CHGNet está carregado e pronto para receber requisições.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "predictor_loaded": true
}
```

### `POST /api/predict`

Envia um arquivo de estrutura cristalina para predição de atividade OER. O arquivo deve conter um óxido de metal de transição.

```bash
curl -X POST http://localhost:8000/api/predict \
  -F "arquivo=@estrutura.cif"
```

**Formatos aceitos:** `.cif`, `.xyz`, `.vasp`

**Exemplo de resposta:**

```json
{
  "formula": "IrO2",
  "band_gap_eV": 0.8214,
  "overpotential_V": 0.1800,
  "is_viable": true,
  "adsorption_energies": {
    "delta_G_O": 2.8200,
    "delta_G_OH": 1.4100,
    "delta_G_OOH": 4.6100
  },
  "inference_time_ms": 1523.45,
  "filename": "estrutura.cif"
}
```

| Campo                  | Descrição                                                          |
| ---------------------- | ------------------------------------------------------------------ |
| `formula`              | Fórmula química reduzida (ex: IrO₂, RuO₂, MnO₂)                  |
| `band_gap_eV`          | Band gap estimado (eV) - 0 = metálico, >3 = isolante              |
| `overpotential_V`      | Overpotential teórico OER (V) - menor = melhor catalisador         |
| `is_viable`            | `true` se η < 0,40 V (catalisador promissor)                      |
| `adsorption_energies`  | Energias de Gibbs de adsorção dos 3 intermediários OER (eV)        |
| `inference_time_ms`    | Tempo total do pipeline (parsing + CHGNet + slab + cálculo) em ms  |
| `filename`             | Nome do arquivo enviado                                            |

**Erros possíveis:**

| Código | Causa                                                        |
| ------ | ------------------------------------------------------------ |
| 400    | Arquivo corrompido ou não é texto UTF-8 válido               |
| 422    | Formato não suportado ou estrutura sem oxigênio/metal de transição |
| 503    | CHGNet ainda não inicializou (aguardar startup)              |

---

## Fluxo de Uso

### Via interface web

1. Acesse http://localhost:8080
2. Na página **Predição OER**, clique em **Selecionar arquivo** e escolha um `.cif`, `.xyz` ou `.vasp`
3. A estrutura 3D é renderizada automaticamente no visualizador (3Dmol.js)
4. Clique em **Analisar Estrutura**
5. Os resultados aparecem:
   - **OER Metrics** - fórmula, overpotential, viabilidade, band gap
   - **Gráfico de dispersão** - posição do material no gráfico de atividade OER
   - **Energias de Adsorção** - ΔG\*OH, ΔG\*O, ΔG\*OOH
   - **Detalhes de Inferência** - tempo de execução

### Via cURL

```bash
# Subir containers
docker compose up -d

# Enviar estrutura CIF para predição
curl -X POST http://localhost:8000/api/predict \
  -F "arquivo=@MnO2.cif"

# Testar com outros formatos
curl -X POST http://localhost:8000/api/predict \
  -F "arquivo=@RuO2.vasp"

curl -X POST http://localhost:8000/api/predict \
  -F "arquivo=@IrO2.xyz"
```

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

### Rebuild

O código é montado via volume bind-mount (hot-reload em dev). Para alterações em `Dockerfile`, `requirements.txt` ou `package.json`:

```bash
docker compose up --build
```

### Linting

```bash
# Frontend (ESLint + Vue)
npm run lint          # auto-fix
npm run lint:check    # apenas verificar
```

### Parar

```bash
docker compose down        # mantém volumes
docker compose down -v     # remove tudo
```

---

## Solução de Problemas

| Problema                           | Solução                                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `predictor_loaded: false`          | CHGNet ainda inicializando. Aguardar e verificar logs: `docker compose logs api_nanoxus`                           |
| Build lento na primeira vez        | Normal - PyTorch + CHGNet + pymatgen ~2 GB. Builds seguintes usam cache                                            |
| `ModuleNotFoundError` no container | Verificar dependências: `docker exec api_nanoxus pip list`                                                         |
| Porta 8000 ou 8080 em uso          | Alterar mapeamento no `docker-compose.yml` (ex: `"8001:8000"`)                                                     |
| Memória insuficiente               | CHGNet + PyTorch requer ~4 GB de RAM. Verificar com `docker stats`                                                 |
| Container reiniciando em loop      | Verificar logs: `docker compose logs api_nanoxus`                                                                  |
| GPU não detectada                  | Instalar NVIDIA Container Toolkit e testar: `docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi` |
| Erro 422 na predição               | Verificar se o arquivo contém oxigênio e pelo menos um metal de transição (Sc–Zn, Y–Cd, La–Hg, Ac)               |
| Erro 503 na predição               | O CHGNet ainda está carregando. Consultar `/health` até `predictor_loaded: true`                                   |

---

## Stack

| Componente         | Tecnologia                | Versão        |
| ------------------ | ------------------------- | ------------- |
| Backend            | Python + FastAPI          | 3.11 / 0.129  |
| Frontend           | Vue.js 3 + Vite           | 3.5 / 7.3     |
| GNN                | CHGNet (PyTorch)          | ≥ 0.4.0       |
| Deep Learning      | PyTorch                   | 2.10          |
| Cristalografia     | pymatgen                  | ≥ 2025.1.0    |
| Grafos             | PyTorch Geometric         | ≥ 2.7.0       |
| Simulação Atômica  | ASE                       | ≥ 3.22        |
| Visualização 3D    | 3Dmol.js                  | 2.5           |
| Gráficos           | Chart.js + vue-chartjs    | 4.5 / 5.3     |
| UI                 | PrimeVue + Tailwind CSS   | 4.5 / 4.1     |
| Containerização    | Docker + Compose          | v2            |
| GPU                | NVIDIA CUDA               | 12.4          |

---

## Referências

- Deng, B. et al. *CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling.* Nature Machine Intelligence **5**, 1031–1041 (2023). - Modelo CHGNet
- Man, I. C. et al. *Universality in Oxygen Evolution Electrocatalysis on Oxide Surfaces.* ChemCatChem **3**, 1159–1165 (2011). - Relações de escala universais para OER
- Nørskov, J. K. et al. *Origin of the Overpotential for Oxygen Reduction at a Fuel-Cell Cathode.* J. Phys. Chem. B **108**, 17886–17892 (2004). - Framework CHE (Computational Hydrogen Electrode)

---
