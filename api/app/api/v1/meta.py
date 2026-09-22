"""Metadatos de la API: alimentan el indicador de estado del frontend."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.dependencias import Configuracion
from app.schemas.classification import InfoApi
from app.seed.modelos import RESUMEN_REGISTRO

router = APIRouter(tags=["meta"])

ETIQUETA_PREPROCESO = "224×224 · CLAHE"


@router.get("/meta", response_model=InfoApi, summary="Información del servicio y del modelo activo")
def obtener_meta(configuracion: Configuracion) -> InfoApi:
    produccion = RESUMEN_REGISTRO["production_model"]
    return InfoApi(
        app_name=configuracion.app_name,
        api_version=configuracion.api_version,
        environment=configuracion.environment,
        data_source=configuracion.data_source,
        simulated_inference=configuracion.simulated_inference,
        model_version=f"{produccion['name']} · {produccion['version']}",
        preprocess_label=ETIQUETA_PREPROCESO,
    )
