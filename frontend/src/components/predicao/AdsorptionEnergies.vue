<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
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
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { RespostaOER } from '@/types'

const props = defineProps<{
  resultado: RespostaOER
}>()

const energias = computed(() => {
  const a = props.resultado.adsorption_energies
  return [
    { label: '*OH', valor: a.delta_G_OH.toFixed(3) },
    { label: '*O', valor: a.delta_G_O.toFixed(3) },
    { label: '*OOH', valor: a.delta_G_OOH.toFixed(3) },
  ]
})
</script>
