<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
    <PageHeader
      titulo="Estrutura Cristalina"
      subtitulo="Envie um .cif, .xyz ou .vasp"
      icone="pi pi-upload"
      cor-fundo="bg-emerald-100 dark:bg-emerald-900/40"
      cor-icone="text-emerald-600 dark:text-emerald-400"
    />

    <FileUpload
      mode="basic"
      :auto="false"
      accept=".cif,.xyz,.vasp"
      :max-file-size="10_000_000"
      choose-label="Selecionar arquivo"
      :choose-icon="'pi pi-folder-open'"
      class="w-full"
      @select="(e: FileUploadSelectEvent) => $emit('selecionar', e)"
    />

    <p class="mt-2 text-xs text-slate-400 dark:text-slate-500">
      Formatos aceitos:
      <span class="font-medium">.cif</span>,
      <span class="font-medium">.xyz</span>,
      <span class="font-medium">.vasp</span>
    </p>

    <div
      v-if="arquivo"
      class="mt-3 flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-surface-800"
    >
      <i class="pi pi-file text-base text-nano-500"></i>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-slate-700 dark:text-slate-200">
          {{ arquivo.name }}
        </p>
        <p class="text-xs text-slate-400 dark:text-slate-500">
          {{ formatarTamanho(arquivo.size) }}
        </p>
      </div>
      <button
        class="flex h-6 w-6 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950/40"
        aria-label="Remover arquivo"
        @click="$emit('limpar')"
      >
        <i class="pi pi-times text-xs"></i>
      </button>
    </div>

    <Button
      label="Analisar Estrutura"
      icon="pi pi-play"
      :loading="carregando"
      :disabled="!temConteudo || carregando"
      size="small"
      class="mt-4 w-full"
      @click="$emit('analisar')"
    />
  </div>
</template>

<script setup lang="ts">
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatarTamanho } from '@/utils/format'

interface FileUploadSelectEvent {
  files: File[]
  originalEvent: Event
}

defineProps<{
  arquivo: File | null
  carregando: boolean
  temConteudo: boolean
}>()

defineEmits<{
  selecionar: [event: FileUploadSelectEvent]
  limpar: []
  analisar: []
}>()
</script>
