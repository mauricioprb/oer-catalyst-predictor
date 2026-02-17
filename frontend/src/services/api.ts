import axios from 'axios'
import type {
  RespostaAnalise,
  RespostaTreinamento,
  ParametrosTreinamento,
  StatusTarefa,
  StatusSaude,
  StatusServico,
} from '@/types'

const http = axios.create({
  baseURL: '/',
  timeout: 120_000,
})

export const apiService = {
  async verificarSaude(): Promise<StatusSaude> {
    const { data } = await http.get<StatusSaude>('/health')
    return data
  },

  async verificarStatus(): Promise<StatusServico> {
    const { data } = await http.get<StatusServico>('/api/status')
    return data
  },

  async analisarImagem(arquivo: File): Promise<RespostaAnalise> {
    const formData = new FormData()
    formData.append('arquivo', arquivo)
    const { data } = await http.post<RespostaAnalise>('/api/analisar-imagem', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async iniciarTreinamento(parametros: Partial<ParametrosTreinamento>): Promise<RespostaTreinamento> {
    const { data } = await http.post<RespostaTreinamento>('/api/iniciar-treinamento', parametros)
    return data
  },

  async consultarTreinamento(idTarefa: string): Promise<StatusTarefa> {
    const { data } = await http.get<StatusTarefa>(`/api/treinamento/${idTarefa}`)
    return data
  },
}
