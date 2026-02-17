<template>
  <div class="space-y-6">
    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
      <PageHeader
        titulo="Enviar Imagem para Análise"
        subtitulo="Formatos aceitos: PNG, JPG, JPEG, TIF, TIFF, BMP"
        icone="pi pi-upload"
      />

      <DropZoneUpload
        ref="dropZoneRef"
        :analisando="analisando"
        @analisar="executarAnalise"
        @limpar="limparResultados"
      />
    </div>

    <transition name="slide-up">
      <ResultadoAnalise
        v-if="resultado"
        :resultado="resultado"
      />
    </transition>

    <transition name="slide-up">
      <div v-if="erro" class="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/40" role="alert">
        <div class="flex items-center gap-3">
          <i class="pi pi-exclamation-circle text-lg text-red-500"></i>
          <div>
            <p class="text-sm font-medium text-red-800 dark:text-red-300">Erro na Análise</p>
            <p class="text-sm text-red-600 dark:text-red-400">{{ erro }}</p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import PageHeader from '@/components/ui/PageHeader.vue'
import DropZoneUpload from '@/components/analise/DropZoneUpload.vue'
import ResultadoAnalise from '@/components/analise/ResultadoAnalise.vue'
import { apiService } from '@/services/api'
import type { RespostaAnalise } from '@/types'

const toast = useToast()
const dropZoneRef = ref<InstanceType<typeof DropZoneUpload> | null>(null)

const analisando = ref(false)
const resultado = ref<RespostaAnalise | null>(null)
const erro = ref<string | null>(null)

function limparResultados() {
  resultado.value = null
  erro.value = null
}

async function executarAnalise(arquivo: File) {
  analisando.value = true
  erro.value = null
  resultado.value = null

  try {
    resultado.value = await apiService.analisarImagem(arquivo)
    toast.add({
      severity: resultado.value.probabilidade_fraude >= 0.5 ? 'warn' : 'success',
      summary: 'Análise Concluída',
      detail: `Classificação: ${resultado.value.classe_predita}`,
      life: 4000,
    })
  } catch (e: any) {
    const mensagem = e.response?.data?.detail ?? e.message ?? 'Erro desconhecido'
    erro.value = mensagem
    toast.add({
      severity: 'error',
      summary: 'Falha na Análise',
      detail: mensagem,
      life: 5000,
    })
  } finally {
    analisando.value = false
  }
}
</script>

<style>
.slide-up-enter-active {
  transition: all 0.3s ease-out;
}
.slide-up-leave-active {
  transition: all 0.2s ease-in;
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
