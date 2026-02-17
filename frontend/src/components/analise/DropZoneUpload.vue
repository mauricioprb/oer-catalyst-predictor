<template>
  <div>
    <div
      class="relative flex min-h-55 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-colors"
      :class="
        arrastando
          ? 'border-nano-400 bg-nano-50 dark:bg-nano-950/30'
          : 'border-slate-300 bg-slate-50 hover:border-nano-300 hover:bg-nano-50/50 dark:border-surface-600 dark:bg-surface-800 dark:hover:border-nano-700 dark:hover:bg-nano-950/30'
      "
      role="button"
      tabindex="0"
      :aria-label="previewUrl ? 'Alterar imagem selecionada' : 'Selecionar imagem para análise'"
      @dragover.prevent="arrastando = true"
      @dragleave.prevent="arrastando = false"
      @drop.prevent="aoSoltar"
      @click="abrirSeletor"
      @keydown.enter="abrirSeletor"
      @keydown.space.prevent="abrirSeletor"
    >
      <input
        ref="inputRef"
        type="file"
        class="hidden"
        accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
        aria-hidden="true"
        @change="aoSelecionar"
      />

      <template v-if="!previewUrl">
        <i class="pi pi-cloud-upload mb-3 text-4xl text-slate-400 dark:text-slate-500"></i>
        <p class="text-sm font-medium text-slate-600 dark:text-slate-300">
          Arraste uma imagem aqui ou <span class="text-nano-600 underline dark:text-nano-400">clique para selecionar</span>
        </p>
        <p class="mt-1 text-xs text-slate-400 dark:text-slate-500">Tamanho máximo recomendado: 10 MB</p>
      </template>

      <template v-else>
        <img
          :src="previewUrl"
          :alt="'Preview de ' + (arquivo?.name ?? 'imagem')"
          class="max-h-50 max-w-full rounded-lg object-contain"
        />
      </template>
    </div>

    <div v-if="arquivo" class="mt-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <i class="pi pi-image text-lg text-slate-500 dark:text-slate-400"></i>
        <div>
          <p class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ arquivo.name }}</p>
          <p class="text-xs text-slate-400 dark:text-slate-500">{{ formatarTamanho(arquivo.size) }}</p>
        </div>
      </div>
      <div class="flex gap-2">
        <Button
          label="Remover"
          icon="pi pi-times"
          severity="secondary"
          text
          size="small"
          @click.stop="onRemover"
        />
        <Button
          label="Analisar Imagem"
          icon="pi pi-search"
          :loading="analisando"
          :disabled="analisando"
          @click.stop="onAnalisar"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import { useFileUpload } from '@/composables/useFileUpload'

defineProps<{
  analisando: boolean
}>()

const emit = defineEmits<{
  analisar: [arquivo: File]
  limpar: []
}>()

const {
  arquivo,
  previewUrl,
  arrastando,
  inputRef,
  abrirSeletor,
  aoSelecionar,
  aoSoltar,
  limpar,
  formatarTamanho,
} = useFileUpload()

function onAnalisar() {
  if (arquivo.value) emit('analisar', arquivo.value)
}

function onRemover() {
  limpar()
  emit('limpar')
}

defineExpose({ limpar })
</script>
