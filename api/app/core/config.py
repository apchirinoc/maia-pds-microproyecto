"""Configuración de la aplicación, leída del entorno.

Toda la configuración entra por variables de entorno (o por el `.env` en
desarrollo). Ningún valor sensible está escrito en el código: el secreto JWT de
`.env.example` es un marcador que el arranque rechaza si se usa en producción.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRETO_DE_EJEMPLO = "cambia-este-secreto-en-produccion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "BrainNeuroScan API"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    allowed_origins: str = "http://localhost:5173"

    jwt_secret: str = SECRETO_DE_EJEMPLO
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15

    demo_username: str = "demo"
    demo_password: str = "demo"

    data_source: Literal["seed", "postgres"] = "seed"
    database_url: str = ""

    inference_engine: Literal["simulated", "onnx"] = "simulated"
    mlflow_tracking_uri: str = ""
    mlflow_model_name: str = "brain-tumor-classifier"
    mlflow_model_alias: str = "champion"

    api_version: str = Field(default="v2.4", description="Versión que muestra la interfaz")

    @property
    def origins(self) -> list[str]:
        return [origen.strip() for origen in self.allowed_origins.split(",") if origen.strip()]

    @property
    def simulated_inference(self) -> bool:
        return self.inference_engine == "simulated"

    @field_validator("jwt_secret")
    @classmethod
    def rechazar_secreto_de_ejemplo(cls, valor: str, info) -> str:
        entorno = (info.data or {}).get("environment")
        if entorno == "production" and valor == SECRETO_DE_EJEMPLO:
            raise ValueError(
                "JWT_SECRET conserva el valor de ejemplo. En producción debe "
                "inyectarse un secreto propio."
            )
        return valor


@lru_cache
def get_settings() -> Settings:
    return Settings()
