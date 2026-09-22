"""Esquemas de clasificación e información del modelo activo."""

from __future__ import annotations

from typing import Literal

from app.schemas.common import EsquemaBase

ClaseTumor = Literal["glioma", "meningioma", "pituitary", "healthy"]


class InfoModeloActivo(EsquemaBase):
    """Lo que la interfaz muestra sobre el modelo que está sirviendo.

    El preproceso lo declara el artefacto (patrón «Transform»); la API sólo lo
    transporta, no lo escribe a mano.
    """

    model_version: str
    preprocess_label: str
    simulated_inference: bool


class ExplicacionPrediccion(EsquemaBase):
    method: Literal["occlusion"]
    method_label: str
    influence_map_data_uri: str


class ResultadoClasificacion(EsquemaBase):
    predicted_class: ClaseTumor
    confidence_by_class: dict[str, float]
    description: str
    model_version: str
    preprocess: str
    country_code: str
    explanation: ExplicacionPrediccion | None = None


class InfoApi(EsquemaBase):
    """Respuesta de `GET /api/v1/meta`, que alimenta el indicador de estado."""

    app_name: str
    api_version: str
    environment: str
    data_source: str
    simulated_inference: bool
    model_version: str
    preprocess_label: str
