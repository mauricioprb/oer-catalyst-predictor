import axios from 'axios'
import type { StatusSaude, RespostaOER } from '@/types'

const http = axios.create({
  baseURL: '/',
  timeout: 120_000,
})

export const apiService = {
  async verificarSaude(): Promise<StatusSaude> {
    const { data } = await http.get<StatusSaude>('/health')
    return data
  },

  async predizirOER(arquivo: File): Promise<RespostaOER> {
    const formData = new FormData()
    formData.append('arquivo', arquivo)
    const { data } = await http.post<RespostaOER>('/api/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
}
