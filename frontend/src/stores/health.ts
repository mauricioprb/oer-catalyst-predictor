import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '@/services/api'

export const useHealthStore = defineStore('health', () => {
  const online = ref(false)
  const modeloCarregado = ref(false)
  const dispositivo = ref('cpu')
  const ultimaVerificacao = ref<Date | null>(null)
  const carregando = ref(false)

  let _intervalo: ReturnType<typeof setInterval> | null = null

  const statusTexto = computed(() => (online.value ? 'Operacional' : 'Indisponível'))
  const dispositivoLabel = computed(() => dispositivo.value.toUpperCase())

  async function verificar() {
    carregando.value = true
    try {
      const saude = await apiService.verificarSaude()
      online.value = saude.status === 'ok'
      modeloCarregado.value = saude.modelo_carregado === 'True'
      dispositivo.value = saude.dispositivo
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
    modeloCarregado,
    dispositivo,
    ultimaVerificacao,
    carregando,
    statusTexto,
    dispositivoLabel,
    verificar,
    iniciarPolling,
    pararPolling,
  }
})
