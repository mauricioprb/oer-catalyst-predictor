<template>
  <div class="grid gap-4 sm:grid-cols-3">
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
</template>

<script setup lang="ts">
import MetricCard from '@/components/ui/MetricCard.vue'
import type { RespostaOER } from '@/types'

defineProps<{
  resultado: RespostaOER
}>()
</script>
