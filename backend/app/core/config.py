from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Nanoxus"
    DEBUG: bool = True
    ARMAZENAMENTO_PATH: Path = Path("/app/armazenamento")
    DADOS_REAIS_PATH: Path = Path("/app/armazenamento/reais")
    DADOS_SINTETICAS_PATH: Path = Path("/app/armazenamento/sinteticas")
    MODELO_PESOS_PATH: Path = Path("/app/armazenamento/pesos")

    class Config:
        env_file = ".env"


settings = Settings()
