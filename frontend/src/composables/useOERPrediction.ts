import { ref } from 'vue'
import { apiService } from '@/services/api'
import type { RespostaOER } from '@/types'

export function useOERPrediction() {
  const carregando = ref(false)
  const resultado = ref<RespostaOER | null>(null)

  async function executarPredicao(arquivo: File): Promise<RespostaOER> {
    carregando.value = true
    resultado.value = null

    try {
      resultado.value = await apiService.predizirOER(arquivo)
      return resultado.value
    } finally {
      carregando.value = false
    }
  }

  function limpar() {
    resultado.value = null
  }

  return {
    carregando,
    resultado,
    executarPredicao,
    limpar,
  }
}
