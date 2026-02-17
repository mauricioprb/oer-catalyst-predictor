<template>
  <div class="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-surface-600 dark:bg-surface-700">
    <div class="flex items-center gap-3 border-b border-slate-200 px-6 py-4 dark:border-surface-600">
      <div
        class="flex h-10 w-10 items-center justify-center rounded-lg"
        :class="ehFraude ? 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400' : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400'"
      >
        <i :class="ehFraude ? 'pi pi-exclamation-triangle' : 'pi pi-check-circle'" class="text-xl"></i>
      </div>
      <div>
        <h3 class="text-base font-semibold text-slate-800 dark:text-slate-100">Resultado da Análise</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ resultado.nome_arquivo }}</p>
      </div>
    </div>

    <div class="p-6">
      <div class="mb-6 flex flex-col items-center">
        <div
          class="mb-3 flex h-28 w-28 items-center justify-center rounded-full border-4"
          :class="ehFraude ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/40' : 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40'"
          role="img"
          :aria-label="'Classificação: ' + resultado.classe_predita"
        >
          <span
            class="text-3xl font-bold"
            :class="ehFraude ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'"
          >
            {{ probabilidadeFormatada }}%
          </span>
        </div>
        <span
          class="inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-semibold"
          :class="ehFraude ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'"
        >
          <i :class="ehFraude ? 'pi pi-times-circle' : 'pi pi-verified'"></i>
          {{ resultado.classe_predita }}
        </span>
      </div>

      <div class="grid gap-4 sm:grid-cols-3">
        <div class="rounded-lg bg-slate-50 p-4 text-center dark:bg-surface-800">
          <p class="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">Probabilidade</p>
          <p class="mt-1 text-xl font-bold text-slate-800 dark:text-slate-100">
            {{ (resultado.probabilidade_fraude * 100).toFixed(2) }}%
          </p>
        </div>
        <div class="rounded-lg bg-slate-50 p-4 text-center dark:bg-surface-800">
          <p class="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">Tempo de Inferência</p>
          <p class="mt-1 text-xl font-bold text-slate-800 dark:text-slate-100">
            {{ resultado.tempo_inferencia_ms.toFixed(1) }} ms
          </p>
        </div>
        <div class="rounded-lg bg-slate-50 p-4 text-center dark:bg-surface-800">
          <p class="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">Dimensões</p>
          <p class="mt-1 text-xl font-bold text-slate-800 dark:text-slate-100">
            {{ resultado.dimensoes_originais[0] }}&times;{{ resultado.dimensoes_originais[1] }}
          </p>
        </div>
      </div>

      <div class="mt-6">
        <p class="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Indicador de Confiança
        </p>
        <ProgressBar
          :value="resultado.probabilidade_fraude * 100"
          :pt="{
            value: {
              class: ehFraude ? '!bg-red-500' : '!bg-emerald-500',
            },
          }"
          style="height: 10px"
          aria-label="Indicador de confiança da predição"
        />
        <div class="mt-1 flex justify-between text-xs text-slate-400 dark:text-slate-500">
          <span>Real</span>
          <span>Sintética</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ProgressBar from 'primevue/progressbar'
import type { RespostaAnalise } from '@/types'

const props = defineProps<{
  resultado: RespostaAnalise
}>()

const ehFraude = computed(() => props.resultado.probabilidade_fraude >= 0.5)
const probabilidadeFormatada = computed(() =>
  (props.resultado.probabilidade_fraude * 100).toFixed(1),
)
</script>
