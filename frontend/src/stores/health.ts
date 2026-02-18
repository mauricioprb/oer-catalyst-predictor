import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '@/services/api'

export const useHealthStore = defineStore('health', () => {
  const online = ref(false)
  const predictorLoaded = ref(false)
  const ultimaVerificacao = ref<Date | null>(null)
  const carregando = ref(false)

  let _intervalo: ReturnType<typeof setInterval> | null = null

  const statusTexto = computed(() => (online.value ? 'Operacional' : 'Indisponível'))

  async function verificar() {
    carregando.value = true
    try {
      const saude = await apiService.verificarSaude()
      online.value = saude.status === 'ok'
      predictorLoaded.value = saude.predictor_loaded === true
      ultimaVerificacao.value = new Date()
    } catch {
      online.value = false
    } finally {
      carregando.value = false
    }
  }

  function iniciarPolling(intervaloMs = 15_000) {
    pararPolling()
    verificar()
    _intervalo = setInterval(verificar, intervaloMs)
  }

  function pararPolling() {
    if (_intervalo) {
      clearInterval(_intervalo)
      _intervalo = null
    }
  }

  return {
    online,
    predictorLoaded,
    ultimaVerificacao,
    carregando,
    statusTexto,
    verificar,
    iniciarPolling,
    pararPolling,
  }
})
