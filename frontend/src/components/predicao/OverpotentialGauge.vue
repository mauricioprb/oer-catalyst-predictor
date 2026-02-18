<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
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
          :style="{ width: `${Math.min((resultado.overpotential_V / escalaMax) * 100, 100)}%` }"
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
      <span>{{ escalaMax.toFixed(1) }} V</span>
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
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { RespostaOER } from '@/types'

const props = defineProps<{
  resultado: RespostaOER
}>()

const escalaMax = computed(() =>
  Math.max(Math.ceil(props.resultado.overpotential_V + 0.5), 2),
)

const limiarPct = computed(() => (0.40 / escalaMax.value) * 100)
</script>
