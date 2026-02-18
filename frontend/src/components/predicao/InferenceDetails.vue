<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
    <PageHeader
      titulo="Detalhes da Inferência"
      icone="pi pi-info-circle"
      cor-fundo="bg-blue-100 dark:bg-blue-900/40"
      cor-icone="text-blue-600 dark:text-blue-400"
    />
    <div class="space-y-2">
      <div
        v-for="item in detalhes"
        :key="item.label"
        class="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-surface-800"
      >
        <span class="text-xs text-slate-500 dark:text-slate-400">{{ item.label }}</span>
        <span class="text-xs font-semibold text-slate-700 dark:text-slate-200">{{ item.valor }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { RespostaOER } from '@/types'

const props = defineProps<{
  resultado: RespostaOER
}>()

const detalhes = computed(() => [
  { label: 'Arquivo', valor: props.resultado.filename },
  { label: 'Tempo', valor: `${props.resultado.inference_time_ms.toFixed(1)} ms` },
  { label: 'Band Gap', valor: `${props.resultado.band_gap_eV.toFixed(3)} eV` },
  { label: 'Overpotential', valor: `${props.resultado.overpotential_V.toFixed(3)} V` },
])
</script>
