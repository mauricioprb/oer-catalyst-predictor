<template>
  <div class="mb-6 flex items-center gap-3">
    <div
      class="flex h-10 w-10 items-center justify-center rounded-lg"
      :class="corFundo"
    >
      <i :class="[icone, corIcone]" class="text-xl"></i>
    </div>
    <div>
      <h2 class="text-base font-semibold text-slate-800 dark:text-slate-100">{{ titulo }}</h2>
      <p v-if="subtitulo" class="text-sm text-slate-500 dark:text-slate-400">{{ subtitulo }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    titulo: string
    subtitulo?: string
    icone: string
    corFundo?: string
    corIcone?: string
  }>(),
  {
    subtitulo: '',
    corFundo: 'bg-nano-100 dark:bg-nano-900/40',
    corIcone: 'text-nano-600 dark:text-nano-400',
  },
)
</script>
