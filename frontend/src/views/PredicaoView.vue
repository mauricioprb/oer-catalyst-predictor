<template>
  <div class="space-y-6">
    <div class="grid gap-6 lg:grid-cols-5">
      <div class="space-y-6 lg:col-span-2">
        <FileUploader
          :arquivo="arquivoSelecionado"
          :carregando="carregando"
          :tem-conteudo="!!cifData"
          @selecionar="aoSelecionarArquivo"
          @limpar="limparTudo"
          @analisar="executarPredicao"
          @colar="aoColarConteudo"
        />

        <transition name="slide-up">
          <InferenceDetails v-if="resultado" :resultado="resultado" />
        </transition>

        <transition name="slide-up">
          <AdsorptionEnergies v-if="resultado" :resultado="resultado" />
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
          <OERMetrics v-if="resultado" :resultado="resultado" />
        </transition>

        <transition name="slide-up">
          <OverpotentialGauge v-if="resultado" :resultado="resultado" />
        </transition>

        <transition name="slide-up">
          <VolcanoPlot v-if="resultado" :resultado="resultado" />
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToast } from 'primevue/usetoast'
import FileUploader from '@/components/predicao/FileUploader.vue'
import MoleculeViewer from '@/components/predicao/MoleculeViewer.vue'
import InferenceDetails from '@/components/predicao/InferenceDetails.vue'
import AdsorptionEnergies from '@/components/predicao/AdsorptionEnergies.vue'
import OverpotentialGauge from '@/components/predicao/OverpotentialGauge.vue'
import VolcanoPlot from '@/components/predicao/VolcanoPlot.vue'
import OERMetrics from '@/components/predicao/OERMetrics.vue'
import { useFileReader } from '@/composables/useFileReader'
import { useOERPrediction } from '@/composables/useOERPrediction'

interface FileUploadSelectEvent {
  files: File[]
  originalEvent: Event
}

const toast = useToast()

const { conteudo: cifData, arquivoSelecionado, validarExtensao, lerArquivo, setManualContent, limpar: limparArquivo } = useFileReader()
const { carregando, resultado, executarPredicao: predizer, limpar: limparPredicao } = useOERPrediction()

function aoSelecionarArquivo(event: FileUploadSelectEvent): void {
  const arquivo = event.files[0]
  if (!arquivo) return

  const extensao = arquivo.name.split('.').pop()?.toLowerCase() ?? ''
  if (!validarExtensao(arquivo.name)) {
    toast.add({
      severity: 'warn',
      summary: 'Formato Inválido',
      detail: `Extensão .${extensao} não aceita. Use: .cif, .xyz ou .vasp`,
      life: 5000,
    })
    return
  }

  lerArquivo(arquivo).catch(() => {
    toast.add({
      severity: 'error',
      summary: 'Erro de Leitura',
      detail: 'Não foi possível ler o arquivo selecionado.',
      life: 5000,
    })
  })
}

function aoColarConteudo(texto: string): void {
  setManualContent(texto)
}

function limparTudo(): void {
  limparArquivo()
  limparPredicao()
}

async function executarPredicao(): Promise<void> {
  if (!arquivoSelecionado.value) return

  try {
    const res = await predizer(arquivoSelecionado.value)
    toast.add({
      severity: res.is_viable ? 'success' : 'info',
      summary: 'Predição Concluída',
      detail: `${res.formula} - η = ${res.overpotential_V.toFixed(3)} V`,
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
  }
}
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
