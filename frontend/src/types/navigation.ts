export interface ItemNavegacao {
  rota: string
  label: string
  icone: string
  descricao?: string
}

export const ITENS_NAVEGACAO: ItemNavegacao[] = [
  {
    rota: '/laboratorio',
    label: 'Laboratório OER',
    icone: 'pi pi-bolt',
    descricao: 'Predição de atividade eletrocatalítica OER',
  },
]
