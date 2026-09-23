"""Metadatos de la API: alimentan el indicador de estado del frontend."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.dependencias import Configuracion
from app.ml.proveedor import MotorInferenciaDep
from app.schemas.classification import InfoApi
from app.seed.modelos import RESUMEN_REGISTRO

router = APIRouter(tags=["meta"])

ETIQUETA_PREPROCESO = "224×224 · CLAHE"


@router.get("/meta", response_model=InfoApi, summary="Información del servicio y del modelo activo")
def obtener_meta(configuracion: Configuracion, motor: MotorInferenciaDep) -> InfoApi:
    if motor is not None:
        info = motor.describe()
        version_modelo, etiqueta_preproceso = info.model_version, info.preprocess_label
    else:
        produccion = RESUMEN_REGISTRO["production_model"]
        version_modelo = f"{produccion['name']} · {produccion['version']}"
        etiqueta_preproceso = ETIQUETA_PREPROCESO
    return InfoApi(
        app_name=configuracion.app_name,
        api_version=configuracion.api_version,
        environment=configuracion.environment,
        data_source=configuracion.data_source,
        simulated_inference=motor is None,
        model_version=version_modelo,
        preprocess_label=etiqueta_preproceso,
    )
