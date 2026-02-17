import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'

const EXTENSOES_VALIDAS = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']
const TAMANHO_MAXIMO_MB = 10

export interface FileUploadState {
  arquivo: ReturnType<typeof ref<File | null>>
  previewUrl: ReturnType<typeof ref<string | null>>
  arrastando: ReturnType<typeof ref<boolean>>
}

/**
 * Composable para gerenciamento de upload de arquivo com preview,
 * validação de extensão e drag-and-drop.
 */
export function useFileUpload() {
  const toast = useToast()
  const arquivo = ref<File | null>(null)
  const previewUrl = ref<string | null>(null)
  const arrastando = ref(false)
  const inputRef = ref<HTMLInputElement | null>(null)

  function validarArquivo(file: File): boolean {
    const extensao = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!EXTENSOES_VALIDAS.includes(extensao)) {
      toast.add({
        severity: 'error',
        summary: 'Formato inválido',
        detail: `Formatos aceitos: ${EXTENSOES_VALIDAS.join(', ')}`,
        life: 5000,
      })
      return false
    }

    if (file.size > TAMANHO_MAXIMO_MB * 1024 * 1024) {
      toast.add({
        severity: 'warn',
        summary: 'Arquivo grande',
        detail: `O arquivo excede ${TAMANHO_MAXIMO_MB} MB. O envio pode demorar.`,
        life: 5000,
      })
    }

    return true
  }

  function processarArquivo(file: File) {
    if (!validarArquivo(file)) return

    arquivo.value = file
    const reader = new FileReader()
    reader.onload = (e) => {
      previewUrl.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }

  function abrirSeletor() {
    inputRef.value?.click()
  }

  function aoSelecionar(event: Event) {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0]
    if (file) processarArquivo(file)
  }

  function aoSoltar(event: DragEvent) {
    arrastando.value = false
    const file = event.dataTransfer?.files?.[0]
    if (file) processarArquivo(file)
  }

  function limpar() {
    arquivo.value = null
    previewUrl.value = null
    if (inputRef.value) inputRef.value.value = ''
  }

  function formatarTamanho(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  return {
    arquivo,
    previewUrl,
    arrastando,
    inputRef,
    abrirSeletor,
    aoSelecionar,
    aoSoltar,
    limpar,
    formatarTamanho,
    EXTENSOES_VALIDAS,
  }
}
