<template>
  <div class="space-y-6">
    <div class="grid gap-6 lg:grid-cols-5">
      <div class="space-y-6 lg:col-span-2">
        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
          <PageHeader
            titulo="Estrutura Cristalina"
            subtitulo="Envie um .cif, .xyz ou .vasp"
            icone="pi pi-upload"
            cor-fundo="bg-emerald-100 dark:bg-emerald-900/40"
            cor-icone="text-emerald-600 dark:text-emerald-400"
          />

          <FileUpload
            mode="basic"
            :auto="false"
            accept=".cif,.xyz,.vasp"
            :max-file-size="10_000_000"
            choose-label="Selecionar arquivo"
          
            :choose-icon="'pi pi-folder-open'"
            class="w-full"
            @select="aoSelecionarArquivo"
          />

          <p class="mt-2 text-xs text-slate-400 dark:text-slate-500">
            Formatos aceitos:
            <span class="font-medium">.cif</span>,
            <span class="font-medium">.xyz</span>,
            <span class="font-medium">.vasp</span>
          </p>

          <div
            v-if="arquivoSelecionado"
            class="mt-3 flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-surface-800"
          >
            <i class="pi pi-file text-base text-nano-500"></i>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-slate-700 dark:text-slate-200">
                {{ arquivoSelecionado.name }}
              </p>
              <p class="text-xs text-slate-400 dark:text-slate-500">
                {{ formatarTamanho(arquivoSelecionado.size) }}
              </p>
            </div>
            <button
              class="flex h-6 w-6 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950/40"
              aria-label="Remover arquivo"
              @click="limparTudo"
            >
              <i class="pi pi-times text-xs"></i>
            </button>
          </div>

          <Button
            label="Analisar Estrutura"
            icon="pi pi-play"
            :loading="carregando"
            :disabled="!cifData || carregando"
            size="small"
            class="mt-4 w-full"
            @click="executarPredicao"
          />
        </div>

        <transition name="slide-up">
          <div
            v-if="resultado"
            class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700"
          >
            <PageHeader
              titulo="Detalhes da Inferência"
              icone="pi pi-info-circle"
              cor-fundo="bg-blue-100 dark:bg-blue-900/40"
              cor-icone="text-blue-600 dark:text-blue-400"
            />
            <div class="space-y-2">
              <div
                v-for="item in detalhesInferencia"
                :key="item.label"
                class="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-surface-800"
              >
                <span class="text-xs text-slate-500 dark:text-slate-400">{{ item.label }}</span>
                <span class="text-xs font-semibold text-slate-700 dark:text-slate-200">{{ item.valor }}</span>
              </div>
            </div>
          </div>
        </transition>

        <transition name="slide-up">
          <div
            v-if="resultado"
            class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700"
          >
            <PageHeader
              titulo="Energias de Adsorção"
              icone="pi pi-chart-bar"
              cor-fundo="bg-violet-100 dark:bg-violet-900/40"
              cor-icone="text-violet-600 dark:text-violet-400"
            />
            <div class="grid grid-cols-3 gap-3">
              <div
                v-for="e in energias"
                :key="e.label"
                class="rounded-lg bg-slate-50 px-3 py-3 text-center dark:bg-surface-800"
              >
                <p class="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                  {{ e.label }}
                </p>
                <p class="mt-1 text-base font-bold text-slate-800 dark:text-slate-100">
                  {{ e.valor }}
                </p>
                <p class="text-[10px] text-slate-400 dark:text-slate-500">eV</p>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <div class="space-y-6 lg:col-span-3">
        <div class="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-surface-600 dark:bg-surface-700">
          <div class="flex items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-surface-600">
            <i class="pi pi-box text-nano-500"></i>
            <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Visualização 3D
            </h3>
          </div>
          <div class="h-96 p-1">
            <MoleculeViewer v-if="cifData" :cif-data="cifData" />
            <div
              v-else
              class="flex h-full items-center justify-center rounded-lg bg-slate-50 dark:bg-surface-800"
            >
              <div class="flex flex-col items-center gap-2">
                <i class="pi pi-box text-4xl text-slate-200 dark:text-surface-600"></i>
                <span class="text-xs text-slate-400 dark:text-slate-500">
                  Envie um arquivo para visualizar
                </span>
              </div>
            </div>
          </div>
        </div>

        <transition name="slide-up">
          <div v-if="resultado" class="grid gap-4 sm:grid-cols-3">
            <MetricCard
              label="Fórmula"
              :valor="resultado.formula"
              icone="pi pi-th-large"
              cor-fundo="bg-nano-100 dark:bg-nano-900/40"
              cor-icone="text-nano-600 dark:text-nano-400"
            />
            <MetricCard
              label="Overpotential"
              :valor="`${resultado.overpotential_V.toFixed(3)} V`"
              icone="pi pi-bolt"
              :cor-fundo="resultado.is_viable ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-red-100 dark:bg-red-900/40'"
              :cor-icone="resultado.is_viable ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
            />
            <MetricCard
              label="Viabilidade"
              :valor="resultado.is_viable ? 'Viável' : 'Não Viável'"
              icone="pi pi-check-circle"
              :cor-fundo="resultado.is_viable ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-red-100 dark:bg-red-900/40'"
              :cor-icone="resultado.is_viable ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
              :descricao="`Band gap: ${resultado.band_gap_eV.toFixed(2)} eV`"
            />
          </div>
        </transition>

        <transition name="slide-up">
          <div
            v-if="resultado"
            class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700"
          >
            <PageHeader
              titulo="Overpotential"
              icone="pi pi-gauge"
              :cor-fundo="resultado.is_viable ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-red-100 dark:bg-red-900/40'"
              :cor-icone="resultado.is_viable ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
            />

            <div class="mb-4 text-center">
              <span
                class="text-4xl font-bold"
                :class="resultado.is_viable ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
              >
                {{ resultado.overpotential_V.toFixed(3) }}
              </span>
              <span class="ml-1 text-lg text-slate-400 dark:text-slate-500">V</span>
            </div>

            <div class="relative mb-6">
              <div class="h-4 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-surface-800">
                <div
                  class="h-full rounded-full transition-all duration-700 ease-out"
                  :class="resultado.is_viable
                    ? 'bg-linear-to-r from-emerald-400 to-emerald-500'
                    : 'bg-linear-to-r from-red-400 to-red-500'"
                  :style="{ width: `${Math.min((resultado.overpotential_V / overpotentialMax) * 100, 100)}%` }"
                ></div>
              </div>

              <div
                class="absolute top-0 h-4 w-0.5 bg-amber-500 dark:bg-amber-400"
                :style="{ left: `${limiarPct}%` }"
              ></div>
              
              <div
                class="absolute top-5 -translate-x-1/2 whitespace-nowrap text-xs font-bold text-amber-600 dark:text-amber-400"
                :style="{ left: `${limiarPct}%` }"
              >
                Limiar: 0.40 V
              </div>
            </div>

            <div class="flex justify-between text-xs text-slate-400 dark:text-slate-500">
              <span>0 V</span>
              <span>{{ overpotentialMax.toFixed(1) }} V</span>
            </div>

            <div class="mt-4 flex justify-center">
              <span
                class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
                :class="resultado.is_viable
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'"
              >
                <i
                  :class="resultado.is_viable ? 'pi pi-check-circle' : 'pi pi-times-circle'"
                  class="text-xs"
                ></i>
                {{ resultado.is_viable ? 'Catalisador Viável' : 'Não Viável' }}
              </span>
            </div>
          </div>
        </transition>

        <transition name="slide-up">
          <div
            v-if="resultado"
            class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700"
          >
            <PageHeader
              titulo="Gráfico de Dispersão - Atividade OER"
              icone="pi pi-chart-scatter"
              cor-fundo="bg-amber-100 dark:bg-amber-900/40"
              cor-icone="text-amber-600 dark:text-amber-400"
            />
            <div class="h-80">
              <Scatter :data="volcanoData" :options="volcanoOptions" />
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import { Scatter } from 'vue-chartjs'
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js'

import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import MoleculeViewer from '@/components/analise/MoleculeViewer.vue'
import { apiService } from '@/services/api'
import type { RespostaOER } from '@/types'
import { useTheme } from '@/composables/useTheme'

ChartJS.register(LinearScale, PointElement, ChartTooltip, Legend)

const toast = useToast()
const { temaEscuro } = useTheme()

const cifData = ref<string>('')
const arquivoSelecionado = ref<File | null>(null)
const carregando = ref(false)
const resultado = ref<RespostaOER | null>(null)

interface FileUploadSelectEvent {
  files: File[]
  originalEvent: Event
}

function aoSelecionarArquivo(event: FileUploadSelectEvent): void {
  const arquivo = event.files[0]
  if (!arquivo) return

  const extensao = arquivo.name.split('.').pop()?.toLowerCase() ?? ''
  const extensoesValidas = ['cif', 'xyz', 'vasp']

  if (!extensoesValidas.includes(extensao)) {
    toast.add({
      severity: 'warn',
      summary: 'Formato Inválido',
      detail: `Extensão .${extensao} não aceita. Use: .cif, .xyz ou .vasp`,
      life: 5000,
    })
    return
  }

  arquivoSelecionado.value = arquivo

  const reader = new FileReader()
  reader.onload = (e) => {
    cifData.value = (e.target?.result as string) ?? ''
  }
  reader.onerror = () => {
    toast.add({
      severity: 'error',
      summary: 'Erro de Leitura',
      detail: 'Não foi possível ler o arquivo selecionado.',
      life: 5000,
    })
  }
  reader.readAsText(arquivo)
}

function limparTudo(): void {
  cifData.value = ''
  arquivoSelecionado.value = null
  resultado.value = null
}

function formatarTamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function executarPredicao(): Promise<void> {
  if (!arquivoSelecionado.value) return

  carregando.value = true
  resultado.value = null

  try {
    resultado.value = await apiService.predizirOER(arquivoSelecionado.value)

    toast.add({
      severity: resultado.value.is_viable ? 'success' : 'info',
      summary: 'Predição Concluída',
      detail: `${resultado.value.formula} — η = ${resultado.value.overpotential_V.toFixed(3)} V`,
      life: 5000,
    })
  } catch (e: unknown) {
    const axiosErr = e as { response?: { data?: { detail?: string } }; message?: string }
    const mensagem = axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Erro desconhecido'
    toast.add({
      severity: 'error',
      summary: 'Falha na Predição',
      detail: mensagem,
      life: 6000,
    })
  } finally {
    carregando.value = false
  }
}

const detalhesInferencia = computed(() => {
  if (!resultado.value) return []
  return [
    { label: 'Arquivo', valor: resultado.value.filename },
    { label: 'Tempo', valor: `${resultado.value.inference_time_ms.toFixed(1)} ms` },
    { label: 'Band Gap', valor: `${resultado.value.band_gap_eV.toFixed(3)} eV` },
    { label: 'Overpotential', valor: `${resultado.value.overpotential_V.toFixed(3)} V` },
  ]
})

const energias = computed(() => {
  if (!resultado.value) return []
  const a = resultado.value.adsorption_energies
  return [
    { label: '*OH', valor: a.delta_G_OH.toFixed(3) },
    { label: '*O', valor: a.delta_G_O.toFixed(3) },
    { label: '*OOH', valor: a.delta_G_OOH.toFixed(3) },
  ]
})

const overpotentialMax = computed(() => {
  if (!resultado.value) return 2
  return Math.max(Math.ceil(resultado.value.overpotential_V + 0.5), 2)
})

const limiarPct = computed(() => {
  return (0.40 / overpotentialMax.value) * 100
})

const REFERENCIAS = [
  { label: 'RuO₂', dg_oh: 1.60, eta: 0.37 },
  { label: 'IrO₂', dg_oh: 1.50, eta: 0.56 },
  { label: 'MnO₂', dg_oh: 0.90, eta: 0.70 },
  { label: 'Co₃O₄', dg_oh: 1.25, eta: 0.48 },
  { label: 'NiOOH', dg_oh: 1.35, eta: 0.52 },
  { label: 'Fe₂O₃', dg_oh: 1.00, eta: 0.85 },
  { label: 'TiO₂', dg_oh: 0.80, eta: 1.19 },
  { label: 'PtO₂', dg_oh: 1.70, eta: 0.65 },
]

const volcanoData = computed(() => {
  const refPoints = REFERENCIAS.map((r) => ({ x: r.dg_oh, y: r.eta }))

  type PointStyle = 'circle' | 'rectRot' | 'triangle' | 'rect' | 'star' | 'dash' | 'cross' | 'crossRot'

  const datasets: {
    label: string
    data: { x: number; y: number }[]
    backgroundColor: string
    borderColor: string
    borderWidth: number
    pointRadius: number
    pointHoverRadius: number
    pointStyle: PointStyle
  }[] = [
    {
      label: 'Referências (literatura)',
      data: refPoints,
      backgroundColor: temaEscuro.value ? 'rgba(148,163,184,0.5)' : '#94a3b8',
      borderColor: temaEscuro.value ? '#94a3b8' : '#64748b',
      borderWidth: 1.5,
      pointRadius: 6,
      pointHoverRadius: 8,
      pointStyle: 'circle',
    },
  ]

  if (resultado.value) {
    datasets.push({
      label: resultado.value.formula,
      data: [
        {
          x: resultado.value.adsorption_energies.delta_G_OH,
          y: resultado.value.overpotential_V,
        },
      ],
      backgroundColor: resultado.value.is_viable ? '#22c55e' : '#ef4444',
      borderColor: resultado.value.is_viable ? '#16a34a' : '#dc2626',
      borderWidth: 2,
      pointRadius: 10,
      pointHoverRadius: 12,
      pointStyle: 'rectRot',
    })
  }

  return { datasets }
})

const volcanoOptions = computed(() => {
  const isDark = temaEscuro.value
  const gridColor = isDark ? 'rgba(100,116,139,0.2)' : 'rgba(148,163,184,0.15)'
  const textColor = isDark ? '#94a3b8' : '#64748b'
  const labelColor = isDark ? '#cbd5e1' : '#475569'

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
          font: { size: 11, family: 'Inter' },
          color: textColor,
        },
      },
      tooltip: {
        backgroundColor: isDark ? '#1e2128' : '#fff',
        titleColor: isDark ? '#e2e8f0' : '#1e293b',
        bodyColor: isDark ? '#cbd5e1' : '#475569',
        borderColor: isDark ? '#363b46' : '#e2e8f0',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        callbacks: {
          label: (ctx: { dataset: { label?: string }; parsed: { x: number | null; y: number | null } }) =>
            `${ctx.dataset.label}: ΔG_OH = ${(ctx.parsed.x ?? 0).toFixed(3)} eV, η = ${(ctx.parsed.y ?? 0).toFixed(3)} V`,
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'ΔG_OH (eV)',
          font: { size: 12, weight: 'bold' as const, family: 'Inter' },
          color: labelColor,
        },
        grid: { color: gridColor },
        ticks: { color: textColor, font: { size: 10 } },
      },
      y: {
        title: {
          display: true,
          text: 'Overpotential η (V)',
          font: { size: 12, weight: 'bold' as const, family: 'Inter' },
          color: labelColor,
        },
        grid: { color: gridColor },
        ticks: { color: textColor, font: { size: 10 } },
        min: 0,
      },
    },
  }
})
</script>

<style>
.slide-up-enter-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-up-leave-active {
  transition: all 0.2s ease-in;
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>