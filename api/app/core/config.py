"""Configuración de la aplicación, leída del entorno.

Toda la configuración entra por variables de entorno (o por el `.env` en
desarrollo). Ningún valor sensible está escrito en el código: el secreto JWT de
`.env.example` es un marcador que el arranque rechaza si se usa en producción.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

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

    # Variables discretas alternativas para PostgreSQL
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_host: str = ""
    postgres_port: int = 5432
    postgres_db: str = ""
    postgres_ssl: str = ""

    inference_engine: Literal["simulated", "onnx"] = "simulated"
    # `mlflow_tracking_uri` selecciona el servidor (el existente o uno nuevo en
    # EC2) sin cambios de código: vacío => registry en memoria (demo/pruebas).
    mlflow_tracking_uri: str = ""
    mlflow_model_name: str = "brain-tumor-classifier"
    mlflow_model_alias: str = "champion"
    mlflow_model_version: str = ""
    mlflow_model_uri: str = ""
    expected_preprocess_fingerprint: str = ""
    inference_concurrency: int = Field(default=2, ge=1, le=16)

    # Acceso a S3 (artifact store de MLflow). Las credenciales las resuelve la
    # cadena por defecto de boto3 (rol IAM en EC2 o variables AWS_*); estas dos
    # solo documentan la región y un endpoint S3 alternativo (p. ej. MinIO).
    aws_region: str = ""
    mlflow_s3_endpoint_url: str = ""

    api_version: str = Field(default="v2.4", description="Versión que muestra la interfaz")

    @model_validator(mode="after")
    def resolver_database_url(self) -> Settings:
        if not self.database_url and self.postgres_host:
            self.database_url = URL.create(
                "postgresql", username=self.postgres_user or None,
                password=self.postgres_password or None, host=self.postgres_host,
                port=self.postgres_port, database=self.postgres_db,
            ).render_as_string(hide_password=False)
        return self

    @property
    def origins(self) -> list[str]:
        return [origen.strip() for origen in self.allowed_origins.split(",") if origen.strip()]

    @property
    def simulated_inference(self) -> bool:
        return self.inference_engine == "simulated"

    @property
    def async_database_url(self) -> str:
        url = self.database_url.strip()
        if not url:
            return ""

        parsed = make_url(url)
        query = dict(parsed.query)
        query.pop("sslmode", None)
        query.pop("ssl", None)

        clean_url = parsed.set(drivername="postgresql+asyncpg", query=query)
        return clean_url.render_as_string(hide_password=False)

    @property
    def needs_ssl(self) -> bool:
        ssl_val = self.postgres_ssl.strip().lower()
        if ssl_val in ("require", "required", "true", "1"):
            return True
        if ssl_val in ("disable", "false", "0"):
            return False

        url_lower = self.database_url.lower()
        if "sslmode=require" in url_lower or "ssl=require" in url_lower:
            return True
        if "supabase.co" in url_lower:
            return True
        return False

    @field_validator("jwt_secret")
    @classmethod
    def rechazar_secreto_de_ejemplo(cls, valor: str, info) -> str:
        entorno = (info.data or {}).get("environment")
        if entorno == "production" and (valor.startswith(SECRETO_DE_EJEMPLO) or len(valor) < 32):
            raise ValueError(
                "JWT_SECRET conserva el valor de ejemplo. En producción debe "
                "inyectarse un secreto propio."
            )
        return valor


@lru_cache
def get_settings() -> Settings:
    return Settings()
