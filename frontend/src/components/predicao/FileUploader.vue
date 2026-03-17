<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
    <PageHeader
      titulo="Estrutura Cristalina"
      subtitulo="Envie um arquivo ou cole o código"
      icone="pi pi-box"
      cor-fundo="bg-emerald-100 dark:bg-emerald-900/40"
      cor-icone="text-emerald-600 dark:text-emerald-400"
    />

    <div class="mb-4">
      <SelectButton
        v-model="modo"
        :options="opcoesModo"
        option-label="label"
        option-value="value"
        aria-labelledby="basic"
        class="w-full"
        :pt="{
          root: 'w-full flex',
          pcToggleButton: {
            root: 'flex-1 justify-center'
          }
        }"
      />
    </div>

    <div v-if="modo === 'upload'" class="space-y-4">
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

      <p class="text-xs text-slate-400 dark:text-slate-500">
        Formatos aceitos:
        <span class="font-medium">.cif</span>,
        <span class="font-medium">.xyz</span>,
        <span class="font-medium">.vasp</span>
      </p>
    </div>

    <div v-else class="space-y-2">
      <Textarea
        v-model="codigoManual"
        rows="8"
        class="w-full font-mono text-xs"
        placeholder="Cole aqui o conteúdo do arquivo (.cif ou .xyz)..."
        @input="$emit('colar', codigoManual)"
      />
      <p class="text-xs text-slate-400 dark:text-slate-500">
        Insira o conteúdo bruto da estrutura.
      </p>
    </div>

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
import { ref, watch } from 'vue'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatarTamanho } from '@/utils/format'

interface FileUploadSelectEvent {
  files: File[]
  originalEvent: Event
}

const props = defineProps<{
  arquivo: File | null
  carregando: boolean
  temConteudo: boolean
}>()

defineEmits<{
  selecionar: [event: FileUploadSelectEvent]
  limpar: []
  analisar: []
  colar: [texto: string]
}>()

const modo = ref('upload')
const opcoesModo = [
  { label: 'Upload', value: 'upload' },
  { label: 'Colar Código', value: 'paste' },
]

const codigoManual = ref('')

watch(
  () => props.arquivo,
  (newVal) => {
    if (!newVal) {
      codigoManual.value = ''
    }
  }
)
</script>
