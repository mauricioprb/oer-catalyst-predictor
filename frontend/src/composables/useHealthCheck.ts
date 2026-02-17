import { onMounted, onUnmounted } from 'vue'
import { useHealthStore } from '@/stores/health'

/**
 * Composable que inicia o polling de saúde da API ao montar
 * e para automaticamente ao desmontar o componente.
 */
export function useHealthCheck(intervaloMs = 15_000) {
  const health = useHealthStore()

  onMounted(() => {
    health.iniciarPolling(intervaloMs)
  })

  onUnmounted(() => {
    health.pararPolling()
  })

  return health
}
