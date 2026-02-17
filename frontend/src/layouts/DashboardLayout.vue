<template>
  <div class="flex min-h-screen flex-col bg-slate-50 dark:bg-surface-900">
    <header
      class="sticky top-0 z-50 border-b border-slate-200 bg-white/90 backdrop-blur-md dark:border-surface-600 dark:bg-surface-800/90"
      role="banner"
    >
      <div class="relative">
        <div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 lg:px-8">
          <router-link
            to="/dashboard"
            class="flex items-center gap-3 transition-opacity hover:opacity-80"
            aria-label="Ir para a página inicial"
          >
            <img src="/images/logo.svg" alt="Nanoxus" class="h-9 w-9" />
            <div class="hidden sm:block">
              <h1 class="text-lg font-bold leading-tight text-slate-900 dark:text-slate-100">Nanoxus</h1>
            </div>
          </router-link>

          <nav class="hidden items-center gap-1 md:flex" aria-label="Navegação principal">
            <router-link
              v-for="item in itensNavegacao"
              :key="item.rota"
              :to="item.rota"
              class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
              :class="
                rotaAtiva(item.rota)
                  ? 'bg-nano-50 text-nano-700 dark:bg-nano-950 dark:text-nano-400'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-surface-700 dark:hover:text-slate-200'
              "
            >
              <i :class="item.icone" class="text-sm"></i>
              <span>{{ item.label }}</span>
            </router-link>
          </nav>

          <div class="flex items-center gap-3">
            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-surface-700 dark:hover:text-slate-200"
              :aria-label="temaEscuro ? 'Ativar tema claro' : 'Ativar tema escuro'"
              @click="alternarTema"
            >
              <i :class="temaEscuro ? 'pi pi-sun' : 'pi pi-moon'" class="text-lg"></i>
            </button>

            <div class="hidden items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 dark:border-surface-600 sm:flex">
              <StatusIndicator :online="health.online" />
              <span class="text-xs font-medium text-slate-500 dark:text-slate-400">
                {{ health.online ? 'API Online' : 'API Offline' }}
              </span>
              <span
                v-if="health.online"
                class="border-l border-slate-200 pl-2 text-xs text-slate-400 dark:border-surface-600 dark:text-slate-500"
              >
                {{ health.dispositivoLabel }}
              </span>
            </div>

            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 md:hidden dark:text-slate-400 dark:hover:bg-surface-700 dark:hover:text-slate-200"
              aria-label="Abrir menu de navegação"
              @click="menuMobileAberto = !menuMobileAberto"
            >
              <i :class="menuMobileAberto ? 'pi pi-times' : 'pi pi-bars'" class="text-lg"></i>
            </button>
          </div>
        </div>

        <transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 -translate-y-2"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 -translate-y-2"
        >
          <div
            v-if="menuMobileAberto"
            class="absolute inset-x-0 top-full z-50 border-t border-slate-200 bg-white px-4 py-3 shadow-lg md:hidden dark:border-surface-600 dark:bg-surface-800"
          >
            <nav class="space-y-1" aria-label="Navegação mobile">
              <router-link
                v-for="item in itensNavegacao"
                :key="item.rota"
                :to="item.rota"
                class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
                :class="
                  rotaAtiva(item.rota)
                    ? 'bg-nano-50 text-nano-700 dark:bg-nano-950 dark:text-nano-400'
                    : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-surface-700'
                "
                @click="menuMobileAberto = false"
              >
                <i :class="item.icone"></i>
                <div>
                  <span>{{ item.label }}</span>
                  <p v-if="item.descricao" class="text-xs font-normal text-slate-400 dark:text-slate-500">
                    {{ item.descricao }}
                  </p>
                </div>
              </router-link>
            </nav>

            <div class="mt-3 flex items-center gap-2 border-t border-slate-100 pt-3 dark:border-surface-600">
              <StatusIndicator :online="health.online" />
              <span class="text-xs text-slate-500 dark:text-slate-400">
                {{ health.online ? 'API Operacional' : 'API Indisponível' }}
                <template v-if="health.online"> · {{ health.dispositivoLabel }}</template>
              </span>
            </div>
          </div>
        </transition>
      </div>
    </header>

    <main class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 lg:px-8 lg:py-8">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer class="border-t border-slate-200 bg-white py-4 dark:border-surface-600 dark:bg-surface-800">
      <div class="mx-auto max-w-7xl px-4 text-center text-xs text-slate-400 dark:text-slate-500 lg:px-8">
        <p>Nanoxus &mdash; Detecção de Fraude em Microscopia Eletrônica</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import StatusIndicator from '@/components/ui/StatusIndicator.vue'
import { useHealthCheck } from '@/composables/useHealthCheck'
import { useTheme } from '@/composables/useTheme'
import { ITENS_NAVEGACAO } from '@/types'

const route = useRoute()
const health = useHealthCheck()
const { temaEscuro, alternarTema } = useTheme()
const menuMobileAberto = ref(false)
const itensNavegacao = ITENS_NAVEGACAO

function rotaAtiva(rota: string): boolean {
  if (rota === '/dashboard') {
    return route.path === '/dashboard'
  }
  return route.path.startsWith(rota)
}
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
