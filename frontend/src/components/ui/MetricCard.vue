<template>
  <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-surface-600 dark:bg-surface-700">
    <div class="flex items-center justify-between">
      <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ label }}</p>
      <div
        class="flex h-9 w-9 items-center justify-center rounded-lg"
        :class="corFundo"
      >
        <i :class="[icone, corIcone]"></i>
      </div>
    </div>
    <p class="mt-2 text-2xl font-bold text-slate-800 dark:text-slate-100">{{ valor }}</p>
    <p v-if="descricao" class="mt-1 text-xs text-slate-400 dark:text-slate-500">{{ descricao }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  valor: string | number
  icone: string
  corFundo: string
  corIcone: string
  descricao?: string
}>()
</script>
