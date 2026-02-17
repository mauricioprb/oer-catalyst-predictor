<template>
  <div class="space-y-6">
    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
      <PageHeader
        titulo="Configurar Treinamento"
        subtitulo="Defina os hiperparâmetros e inicie o processo"
        icone="pi pi-cog"
        cor-fundo="bg-amber-100 dark:bg-amber-900/40"
        cor-icone="text-amber-600 dark:text-amber-400"
      />

      <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <div class="space-y-1.5">
          <label for="epocas" class="block text-sm font-medium text-slate-700 dark:text-slate-300">Número de Épocas</label>
          <InputNumber
            id="epocas"
            v-model="form.epochs"
            :min="1"
            :max="500"
            show-buttons
            fluid
            aria-describedby="epocas-help"
          />
          <small id="epocas-help" class="text-xs text-slate-400 dark:text-slate-500">Iterações completas sobre o dataset</small>
        </div>

        <div class="space-y-1.5">
          <label for="lote" class="block text-sm font-medium text-slate-700 dark:text-slate-300">Tamanho do Lote</label>
          <InputNumber
            id="lote"
            v-model="form.batch_size"
            :min="2"
            :max="128"
            :step="2"
            show-buttons
            fluid
            aria-describedby="lote-help"
          />
          <small id="lote-help" class="text-xs text-slate-400 dark:text-slate-500">Amostras por iteração (batch size)</small>
        </div>

        <div class="space-y-1.5">
          <label for="lr" class="block text-sm font-medium text-slate-700 dark:text-slate-300">Taxa de Aprendizado</label>
          <InputNumber
            id="lr"
            v-model="form.learning_rate"
            :min="0.000001"
            :max="0.1"
            :min-fraction-digits="4"
            :max-fraction-digits="6"
            mode="decimal"
            fluid
            aria-describedby="lr-help"
          />
          <small id="lr-help" class="text-xs text-slate-400 dark:text-slate-500">Learning rate inicial (AdamW)</small>
        </div>

        <div class="space-y-1.5">
          <label for="arquitetura" class="block text-sm font-medium text-slate-700 dark:text-slate-300">Arquitetura</label>
          <Select
            id="arquitetura"
            v-model="form.arquitetura"
            :options="arquiteturas"
            option-label="label"
            option-value="value"
            fluid
            aria-describedby="arq-help"
          />
          <small id="arq-help" class="text-xs text-slate-400 dark:text-slate-500">Backbone da rede neural</small>
        </div>

        <div class="space-y-1.5">
          <label for="paciencia" class="block text-sm font-medium text-slate-700 dark:text-slate-300">Paciência (Early Stop)</label>
          <InputNumber
            id="paciencia"
            v-model="form.early_stop_patience"
            :min="1"
            :max="50"
            show-buttons
            fluid
            aria-describedby="paciencia-help"
          />
          <small id="paciencia-help" class="text-xs text-slate-400 dark:text-slate-500">Épocas sem melhora para interromper</small>
        </div>

        <div class="flex items-end pb-1">
          <div class="flex w-full items-center gap-3 rounded-lg bg-slate-50 px-4 py-3 dark:bg-surface-800">
            <ToggleSwitch
              v-model="form.use_mock"
              input-id="mock"
              aria-describedby="mock-help"
            />
            <div>
              <label for="mock" class="cursor-pointer text-sm font-medium text-slate-700 dark:text-slate-300">Dados Mock</label>
              <p id="mock-help" class="text-xs text-slate-400 dark:text-slate-500">Gerar dados sintéticos de teste</p>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-6 flex flex-col items-stretch gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between dark:border-surface-600">
        <p class="text-xs text-slate-400 dark:text-slate-500">
          O treinamento roda em background — a interface continua acessível.
        </p>
        <Button
          label="Iniciar Treinamento"
          icon="pi pi-play"
          size="small"
          :loading="iniciando"
          :disabled="iniciando || tarefaAtiva !== null"
          @click="iniciar"
        />
      </div>
    </div>

    <transition name="slide-up">
      <div
        v-if="tarefaAtiva"
        class="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-surface-600 dark:bg-surface-700"
      >
        <div class="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-surface-600">
          <div class="flex items-center gap-3">
            <div
              class="flex h-10 w-10 items-center justify-center rounded-lg"
              :class="corEstado.bg"
            >
              <i
                :class="[iconeEstado, corEstado.texto]"
                class="text-xl"
                :style="statusTarefa?.estado === 'em_execucao' ? 'animation: spin 1s linear infinite' : ''"
              ></i>
            </div>
            <div>
              <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200">
                {{ labelEstado }}
              </h3>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                Tarefa: <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs dark:bg-surface-800">{{ tarefaAtiva }}</code>
              </p>
            </div>
          </div>
          <Button
            v-if="statusTarefa?.estado === 'concluido' || statusTarefa?.estado === 'erro'"
            icon="pi pi-times"
            text
            rounded
            severity="secondary"
            aria-label="Fechar resultado"
            @click="fecharTarefa"
          />
        </div>

        <div class="p-6">
          <div v-if="statusTarefa?.estado === 'em_execucao'" class="space-y-3">
            <ProgressBar mode="indeterminate" style="height: 6px" aria-label="Treinamento em andamento" />
            <p class="text-center text-sm text-slate-500 dark:text-slate-400">
              Processando épocas... Iniciado em {{ statusTarefa.data_inicio }}
            </p>
          </div>

          <div v-if="statusTarefa?.estado === 'concluido' && statusTarefa.resultado" class="space-y-5">
            <div class="grid gap-4 sm:grid-cols-3">
              <div class="rounded-lg bg-emerald-50 p-4 text-center dark:bg-emerald-900/30">
                <p class="text-xs font-medium uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Melhor Acurácia</p>
                <p class="mt-1 text-2xl font-bold text-emerald-700 dark:text-emerald-300">
                  {{ (statusTarefa.resultado.melhor_acuracia_validacao * 100).toFixed(1) }}%
                </p>
              </div>
              <div class="rounded-lg bg-nano-50 p-4 text-center dark:bg-nano-900/30">
                <p class="text-xs font-medium uppercase tracking-wider text-nano-600 dark:text-nano-400">Melhor Época</p>
                <p class="mt-1 text-2xl font-bold text-nano-700 dark:text-nano-300">
                  {{ statusTarefa.resultado.melhor_epoca }}
                </p>
              </div>
              <div class="rounded-lg bg-slate-50 p-4 text-center dark:bg-surface-800">
                <p class="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">Total de Épocas</p>
                <p class="mt-1 text-2xl font-bold text-slate-700 dark:text-slate-200">
                  {{ statusTarefa.resultado.total_epocas }}
                </p>
              </div>
            </div>

            <DataTable
              :value="statusTarefa.resultado.epocas"
              striped-rows
              size="small"
              scrollable
              scroll-height="320px"
              :pt="{ header: { class: '!bg-slate-50 dark:!bg-surface-800' } }"
              aria-label="Métricas por época de treinamento"
            >
              <Column field="epoca" header="Época" style="min-width: 70px" />
              <Column header="Perda Treino" style="min-width: 110px">
                <template #body="{ data }">{{ data.perda_treino.toFixed(4) }}</template>
              </Column>
              <Column header="Acc. Treino" style="min-width: 110px">
                <template #body="{ data }">
                  <span class="font-medium">{{ (data.acuracia_treino * 100).toFixed(1) }}%</span>
                </template>
              </Column>
              <Column header="Perda Valid." style="min-width: 110px">
                <template #body="{ data }">{{ data.perda_validacao.toFixed(4) }}</template>
              </Column>
              <Column header="Acc. Valid." style="min-width: 110px">
                <template #body="{ data }">
                  <Tag
                    :severity="data.acuracia_validacao >= 0.8 ? 'success' : data.acuracia_validacao >= 0.6 ? 'warn' : 'danger'"
                    :value="(data.acuracia_validacao * 100).toFixed(1) + '%'"
                  />
                </template>
              </Column>
              <Column header="Duração" style="min-width: 90px">
                <template #body="{ data }">{{ data.duracao_segundos.toFixed(1) }}s</template>
              </Column>
              <Column header="LR" style="min-width: 100px">
                <template #body="{ data }">{{ data.learning_rate.toExponential(2) }}</template>
              </Column>
            </DataTable>
          </div>

          <div v-if="statusTarefa?.estado === 'erro'" class="rounded-lg bg-red-50 p-4 dark:bg-red-950/40" role="alert">
            <div class="flex items-center gap-2">
              <i class="pi pi-exclamation-circle text-red-500"></i>
              <p class="text-sm font-medium text-red-800 dark:text-red-300">Erro no Treinamento</p>
            </div>
            <p class="mt-2 text-sm text-red-600 dark:text-red-400">{{ statusTarefa.erro }}</p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import ProgressBar from 'primevue/progressbar'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import PageHeader from '@/components/ui/PageHeader.vue'
import { apiService } from '@/services/api'
import type { StatusTarefa } from '@/types'

const toast = useToast()

const form = ref({
  epochs: 30,
  batch_size: 32,
  learning_rate: 0.0001,
  arquitetura: 'resnet18',
  use_mock: false,
  early_stop_patience: 10,
})

const arquiteturas = [
  { label: 'ResNet-18', value: 'resnet18' },
  { label: 'ResNet-34', value: 'resnet34' },
  { label: 'EfficientNet-B0', value: 'efficientnet_b0' },
]

const iniciando = ref(false)
const tarefaAtiva = ref<string | null>(null)
const statusTarefa = ref<StatusTarefa | null>(null)

let intervaloPolling: ReturnType<typeof setInterval> | null = null

const iconeEstado = computed(() => {
  switch (statusTarefa.value?.estado) {
    case 'enfileirado': return 'pi pi-clock'
    case 'em_execucao': return 'pi pi-spinner'
    case 'concluido': return 'pi pi-check-circle'
    case 'erro': return 'pi pi-times-circle'
    default: return 'pi pi-clock'
  }
})

const labelEstado = computed(() => {
  switch (statusTarefa.value?.estado) {
    case 'enfileirado': return 'Aguardando Início'
    case 'em_execucao': return 'Treinamento em Andamento'
    case 'concluido': return 'Treinamento Concluído'
    case 'erro': return 'Falha no Treinamento'
    default: return 'Aguardando...'
  }
})

const corEstado = computed(() => {
  switch (statusTarefa.value?.estado) {
    case 'em_execucao': return { bg: 'bg-amber-100 dark:bg-amber-900/40', texto: 'text-amber-600 dark:text-amber-400' }
    case 'concluido': return { bg: 'bg-emerald-100 dark:bg-emerald-900/40', texto: 'text-emerald-600 dark:text-emerald-400' }
    case 'erro': return { bg: 'bg-red-100 dark:bg-red-900/40', texto: 'text-red-600 dark:text-red-400' }
    default: return { bg: 'bg-slate-100 dark:bg-surface-800', texto: 'text-slate-500 dark:text-slate-400' }
  }
})

async function iniciar() {
  iniciando.value = true
  try {
    const resposta = await apiService.iniciarTreinamento(form.value)
    tarefaAtiva.value = resposta.id_tarefa

    toast.add({
      severity: 'info',
      summary: 'Treinamento Iniciado',
      detail: `Tarefa ${resposta.id_tarefa} em andamento`,
      life: 4000,
    })

    iniciarPolling()
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Erro ao Iniciar',
      detail: e.response?.data?.detail ?? e.message,
      life: 5000,
    })
  } finally {
    iniciando.value = false
  }
}

function iniciarPolling() {
  pararPolling()
  consultarStatus()
  intervaloPolling = setInterval(consultarStatus, 5_000)
}

function pararPolling() {
  if (intervaloPolling) {
    clearInterval(intervaloPolling)
    intervaloPolling = null
  }
}

async function consultarStatus() {
  if (!tarefaAtiva.value) return
  try {
    statusTarefa.value = await apiService.consultarTreinamento(tarefaAtiva.value)
    if (statusTarefa.value.estado === 'concluido' || statusTarefa.value.estado === 'erro') {
      pararPolling()
      if (statusTarefa.value.estado === 'concluido') {
        toast.add({
          severity: 'success',
          summary: 'Treinamento Concluído',
          detail: `Melhor acurácia: ${((statusTarefa.value.resultado?.melhor_acuracia_validacao ?? 0) * 100).toFixed(1)}%`,
          life: 6000,
        })
      }
    }
  } catch { /* silent */ }
}

function fecharTarefa() {
  pararPolling()
  tarefaAtiva.value = null
  statusTarefa.value = null
}

onUnmounted(() => pararPolling())
</script>

<style>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-leave-active { transition: all 0.2s ease-in; }
.slide-up-enter-from { opacity: 0; transform: translateY(16px); }
.slide-up-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
