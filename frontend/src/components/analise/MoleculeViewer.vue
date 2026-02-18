<template>
  <div
    ref="containerRef"
    class="molecule-viewer relative h-full w-full min-h-80 overflow-hidden rounded-lg bg-white dark:bg-surface-800"
    role="img"
    aria-label="Visualizador 3D de estrutura cristalina"
  >
    <div
      v-if="isLoading"
      class="absolute inset-0 z-10 flex items-center justify-center bg-white/80 dark:bg-surface-800/80"
    >
      <div class="flex flex-col items-center gap-3">
        <i class="pi pi-spin pi-spinner text-3xl text-nano-500"></i>
        <span class="text-sm font-medium text-slate-500 dark:text-slate-400">
          Carregando estrutura…
        </span>
      </div>
    </div>

    <div
      v-if="errorMessage"
      class="absolute inset-0 z-10 flex items-center justify-center bg-white dark:bg-surface-800"
    >
      <div class="flex flex-col items-center gap-2 text-center px-6">
        <i class="pi pi-exclamation-triangle text-3xl text-red-400"></i>
        <p class="text-sm font-medium text-red-600 dark:text-red-400">
          {{ errorMessage }}
        </p>
      </div>
    </div>

    <div
      ref="viewerRef"
      class="h-full w-full"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import * as $3Dmol from '3dmol'
import { useTheme } from '@/composables/useTheme'

interface Props {
  cifData: string
}

const props = defineProps<Props>()

const { temaEscuro } = useTheme()
const bgColor = computed(() => (temaEscuro.value ? '#1a1d22' : '#ffffff'))

const containerRef = ref<HTMLDivElement | null>(null)
const viewerRef = ref<HTMLDivElement | null>(null)

let viewer: $3Dmol.GLViewer | null = null
let resizeObserver: ResizeObserver | null = null

const isLoading = ref(false)
const errorMessage = ref('')

function detectFormat(content: string): string {
  const trimmed = content.trim()

  const lines = trimmed.split('\n')
  if (lines.length >= 5) {
    const secondLine = lines[1].trim()
    if (/^\d+(\.\d+)?$/.test(secondLine)) return 'vasp'
  }

  if (/^\d+\s*$/.test(lines[0].trim()) && lines.length > 2) return 'xyz'

  return 'cif'
}

onMounted(async () => {
  await nextTick()

  initViewer()

  if (props.cifData) {
    loadModel(props.cifData)
  }

  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (viewer) {
        viewer.resize()
        viewer.render()
      }
    })
    resizeObserver.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  destroyViewer()
})

watch(
  () => props.cifData,
  async (newData: string) => {
    if (newData) {
      await nextTick()
      loadModel(newData)
    }
  },
)

watch(bgColor, (color: string) => {
  if (viewer) {
    viewer.setBackgroundColor(color)
    viewer.render()
  }
})

function initViewer(): void {
  if (!viewerRef.value) return

  try {
    viewer = $3Dmol.createViewer(viewerRef.value, {
      backgroundColor: bgColor.value,
      antialias: true,
      cartoonQuality: 8,
    })
    viewer.resize()
  } catch (err) {
    console.error('[MoleculeViewer] Falha ao criar GLViewer:', err)
    errorMessage.value = 'Não foi possível inicializar o visualizador 3D.'
  }
}

function loadModel(content: string): void {
  if (!viewer) initViewer()
  if (!viewer) return

  isLoading.value = true
  errorMessage.value = ''

  try {
    viewer.removeAllModels()
    viewer.removeAllSurfaces()
    viewer.removeAllLabels()
    viewer.removeAllSurfaces()

    const fmt = detectFormat(content)

    const opts = fmt === 'cif'
      ? { doAssembly: true, duplicateAssemblyAtoms: true, normalizeAssembly: true }
      : {}

    viewer.addModel(content, fmt, opts)

    viewer.setStyle({}, {
      sphere: { scale: 0.3, colorscheme: 'Jmol' },
      stick:  { radius: 0.15, colorscheme: 'Jmol' },
    })

    if (fmt === 'cif' || fmt === 'vasp') {
      viewer.addUnitCell()
    }

    viewer.resize()
    viewer.zoomTo()
    viewer.zoom(0.85) 
    viewer.render()

    setTimeout(() => {
      if (viewer) {
        viewer.resize()
        viewer.zoomTo()
        viewer.zoom(0.85)
        viewer.render()
      }
    }, 150)

    isLoading.value = false
  } catch (err) {
    console.error('[MoleculeViewer] Falha ao carregar modelo:', err)
    errorMessage.value = 'Erro ao interpretar a estrutura cristalina.'
    isLoading.value = false
  }
}

function destroyViewer(): void {
  if (viewer) {
    viewer.removeAllModels()
    viewer.removeAllSurfaces()
    viewer.removeAllLabels()
    viewer.removeAllSurfaces()
    viewer = null
  }
}
</script>

<style scoped>
.molecule-viewer :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  display: block;
  border-radius: inherit;
}
</style>
