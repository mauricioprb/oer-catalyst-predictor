import { ref } from 'vue'

export function useFileReader() {
  const conteudo = ref('')
  const arquivoSelecionado = ref<File | null>(null)

  const extensoesValidas = ['cif', 'xyz', 'vasp']

  function validarExtensao(nomeArquivo: string): boolean {
    const extensao = nomeArquivo.split('.').pop()?.toLowerCase() ?? ''
    return extensoesValidas.includes(extensao)
  }

  function lerArquivo(arquivo: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const texto = (e.target?.result as string) ?? ''
        conteudo.value = texto
        arquivoSelecionado.value = arquivo
        resolve(texto)
      }
      reader.onerror = () => {
        reject(new Error('Não foi possível ler o arquivo selecionado.'))
      }
      reader.readAsText(arquivo)
    })
  }

  function setManualContent(texto: string, nome = 'estrutura_colada.cif') {
    conteudo.value = texto
    if (texto.trim()) {
      arquivoSelecionado.value = new File([texto], nome, { type: 'text/plain' })
    } else {
      arquivoSelecionado.value = null
    }
  }

  function limpar() {
    conteudo.value = ''
    arquivoSelecionado.value = null
  }

  return {
    conteudo,
    arquivoSelecionado,
    extensoesValidas,
    validarExtensao,
    lerArquivo,
    setManualContent,
    limpar,
  }
}
