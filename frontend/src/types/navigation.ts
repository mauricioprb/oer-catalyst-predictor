export interface ItemNavegacao {
  rota: string
  label: string
  icone: string
  descricao?: string
}

export const ITENS_NAVEGACAO: ItemNavegacao[] = [
  {
    rota: '/dashboard',
    label: 'Visão Geral',
    icone: 'pi pi-objects-column',
    descricao: 'Status do sistema e guia rápido',
  },
  {
    rota: '/dashboard/analise',
    label: 'Análise',
    icone: 'pi pi-search',
    descricao: 'Verificar autenticidade de imagens',
  },
  {
    rota: '/dashboard/treinamento',
    label: 'Treinamento',
    icone: 'pi pi-cog',
    descricao: 'Configurar e executar treinamento',
  },
]
