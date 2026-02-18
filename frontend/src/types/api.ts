
export interface StatusSaude {
  status: string
  predictor_loaded: boolean
}

export interface EnergiaAdsorcao {
  delta_G_O: number
  delta_G_OH: number
  delta_G_OOH: number
}

export interface RespostaOER {
  formula: string
  band_gap_eV: number
  overpotential_V: number
  is_viable: boolean
  adsorption_energies: EnergiaAdsorcao
  inference_time_ms: number
  filename: string
}
