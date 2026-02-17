export interface RespostaAnalise {
  probabilidade_fraude: number
  classe_predita: string
  tempo_inferencia_ms: number
  nome_arquivo: string
  dimensoes_originais: number[]
}

export interface RespostaTreinamento {
  id_tarefa: string
  mensagem: string
  data_inicio: string
}

export interface ParametrosTreinamento {
  epochs: number
  batch_size: number
  learning_rate: number
  arquitetura: string
  use_mock: boolean
  early_stop_patience: number
}

export interface MetricaEpoca {
  epoca: number
  perda_treino: number
  acuracia_treino: number
  perda_validacao: number
  acuracia_validacao: number
  duracao_segundos: number
  learning_rate: number
}

export interface ResultadoTreinamento {
  melhor_acuracia_validacao: number
  melhor_epoca: number
  total_epocas: number
  epocas: MetricaEpoca[]
}

export interface StatusTarefa {
  estado: 'enfileirado' | 'em_execucao' | 'concluido' | 'erro'
  data_inicio: string
  parametros: ParametrosTreinamento
  resultado: ResultadoTreinamento | null
  erro: string | null
}

export interface StatusSaude {
  status: string
  modelo_carregado: string
  dispositivo: string
}

export interface StatusServico {
  servico: string
  estado: string
}
