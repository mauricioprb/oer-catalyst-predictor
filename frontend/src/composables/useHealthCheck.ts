import { onMounted, onUnmounted } from 'vue'
import { useHealthStore } from '@/stores/health'

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
