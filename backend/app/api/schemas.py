from __future__ import annotations

from pydantic import BaseModel, Field


class AdsorptionEnergies(BaseModel):
    delta_G_O: float = Field(..., description="ΔG de adsorção do *O (eV)")
    delta_G_OH: float = Field(..., description="ΔG de adsorção do *OH (eV)")
    delta_G_OOH: float = Field(..., description="ΔG de adsorção do *OOH (eV)")


class PredictionResponse(BaseModel):
    formula: str = Field(..., description="Fórmula química reduzida do material")
    band_gap_eV: float = Field(..., description="Band gap estimado (eV)")
    overpotential_V: float = Field(..., description="Overpotential teórico OER (V)")
    is_viable: bool = Field(..., description="True se overpotential < 0.40 V")
    adsorption_energies: AdsorptionEnergies
    inference_time_ms: float = Field(..., description="Tempo de inferência em milissegundos")
    filename: str = Field(..., description="Nome do arquivo enviado")


class ErrorResponse(BaseModel):
    detail: str
