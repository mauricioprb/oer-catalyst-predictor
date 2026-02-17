<template>
  <div class="space-y-6">
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        v-for="card in cards"
        :key="card.label"
        :label="card.label"
        :valor="card.valor"
        :icone="card.icone"
        :cor-fundo="card.corFundo"
        :cor-icone="card.corIcone"
        :descricao="card.descricao"
      />
    </div>

    <div class="grid gap-6 lg:grid-cols-2">
      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
        <PageHeader
          titulo="Status do Sistema"
          icone="pi pi-server"
        />

        <div class="space-y-3">
          <div
            v-for="item in itensStatus"
            :key="item.label"
            class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 dark:bg-surface-800"
          >
            <span class="text-sm text-slate-600 dark:text-slate-300">{{ item.label }}</span>
            <span
              class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
              :class="item.tagClass"
            >
              <span class="inline-block h-1.5 w-1.5 rounded-full" :class="item.dotClass"></span>
              {{ item.valor }}
            </span>
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
        <PageHeader
          titulo="Modelo em Memória"
          icone="pi pi-microchip"
          cor-fundo="bg-violet-100 dark:bg-violet-900/40"
          cor-icone="text-violet-600 dark:text-violet-400"
        />

        <div class="space-y-3">
          <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 dark:bg-surface-800">
            <span class="text-sm text-slate-600 dark:text-slate-300">Arquitetura</span>
            <span class="text-sm font-medium text-slate-800 dark:text-slate-200">ResNet-18</span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 dark:bg-surface-800">
            <span class="text-sm text-slate-600 dark:text-slate-300">Pesos</span>
            <span class="text-sm font-medium text-slate-800 dark:text-slate-200">
              {{ health.modeloCarregado ? 'Carregados' : 'ImageNet (padrão)' }}
            </span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 dark:bg-surface-800">
            <span class="text-sm text-slate-600 dark:text-slate-300">Dispositivo</span>
            <Tag :value="health.dispositivoLabel" :severity="health.dispositivo === 'cuda' ? 'success' : 'info'" />
          </div>
          <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 dark:bg-surface-800">
            <span class="text-sm text-slate-600 dark:text-slate-300">Status</span>
            <Tag :value="health.modeloCarregado ? 'Pronto' : 'Não carregado'" :severity="health.modeloCarregado ? 'success' : 'warn'" />
          </div>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
      <PageHeader
        titulo="Guia Rápido"
        icone="pi pi-book"
        cor-fundo="bg-amber-100 dark:bg-amber-900/40"
        cor-icone="text-amber-600 dark:text-amber-400"
      />

      <div class="grid gap-4 sm:grid-cols-3">
        <router-link
          v-for="passo in passos"
          :key="passo.numero"
          :to="passo.rota"
          class="group rounded-lg border border-slate-100 p-4 transition-colors hover:border-nano-200 hover:bg-nano-50/30 dark:border-surface-600 dark:hover:border-nano-800 dark:hover:bg-nano-950/30"
        >
          <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-nano-100 text-sm font-bold text-nano-700 transition-colors group-hover:bg-nano-600 group-hover:text-white dark:bg-nano-950 dark:text-nano-400 dark:group-hover:bg-nano-600 dark:group-hover:text-white">
            {{ passo.numero }}
          </div>
          <h4 class="text-sm font-semibold text-slate-800 dark:text-slate-200">{{ passo.titulo }}</h4>
          <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ passo.descricao }}</p>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useHealthStore } from '@/stores/health'

const health = useHealthStore()

const cards = computed(() => [
  {
    label: 'API',
    valor: health.online ? 'Online' : 'Offline',
    descricao: 'Estado do serviço backend',
    icone: 'pi pi-server',
    corFundo: health.online ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-red-100 dark:bg-red-900/40',
    corIcone: health.online ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400',
  },
  {
    label: 'Modelo',
    valor: health.modeloCarregado ? 'Carregado' : 'Ausente',
    descricao: 'Detector de fraude na memória',
    icone: 'pi pi-microchip',
    corFundo: health.modeloCarregado ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-amber-100 dark:bg-amber-900/40',
    corIcone: health.modeloCarregado ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400',
  },
  {
    label: 'Dispositivo',
    valor: health.dispositivoLabel,
    descricao: 'Hardware de inferência',
    icone: 'pi pi-bolt',
    corFundo: 'bg-violet-100 dark:bg-violet-900/40',
    corIcone: 'text-violet-600 dark:text-violet-400',
  },
  {
    label: 'Formatos',
    valor: '6 tipos',
    descricao: 'PNG, JPG, JPEG, TIF, TIFF, BMP',
    icone: 'pi pi-image',
    corFundo: 'bg-nano-100 dark:bg-nano-900/40',
    corIcone: 'text-nano-600 dark:text-nano-400',
  },
])

const itensStatus = computed(() => [
  {
    label: 'Serviço FastAPI',
    valor: health.online ? 'Operacional' : 'Indisponível',
    tagClass: health.online ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
    dotClass: health.online ? 'bg-emerald-500' : 'bg-red-500',
  },
  {
    label: 'Interface Vue.js',
    valor: 'Operacional',
    tagClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
    dotClass: 'bg-emerald-500',
  },
  {
    label: 'Rede Docker',
    valor: 'Conectada',
    tagClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
    dotClass: 'bg-emerald-500',
  },
])

const passos = [
  {
    numero: 1,
    titulo: 'Treine o Modelo',
    descricao: 'Acesse a página de Treinamento e configure os hiperparâmetros. Use dados mock para testes ou imagens reais para resultados concretos.',
    rota: '/dashboard/treinamento',
  },
  {
    numero: 2,
    titulo: 'Envie uma Imagem',
    descricao: 'Na página de Análise, arraste ou selecione uma imagem de microscopia eletrônica para verificação de autenticidade.',
    rota: '/dashboard/analise',
  },
  {
    numero: 3,
    titulo: 'Veja o Resultado',
    descricao: 'O sistema retorna a probabilidade de fraude, a classificação (Real ou Sintética) e o tempo de inferência.',
    rota: '/dashboard/analise',
  },
]
</script>
