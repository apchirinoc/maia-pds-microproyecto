"""Metadatos de la API: alimentan el indicador de estado del frontend."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.v1.dependencias import Configuracion
from app.schemas.classification import InfoApi

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=InfoApi, summary="Información del servicio y del modelo activo")
def obtener_meta(configuracion: Configuracion, request: Request) -> InfoApi:
    engine = getattr(request.app.state, "inference_engine", None)
    info = engine.describe() if engine is not None else None
    return InfoApi(
        app_name=configuracion.app_name,
        api_version=configuracion.api_version,
        environment=configuracion.environment,
        data_source=configuracion.data_source,
        simulated_inference=info.simulated if info else configuracion.simulated_inference,
        model_version=f"{info.model_name} · {info.model_version}" if info else "",
        preprocess_label=info.preprocess_label if info else "",
        model_ready=info is not None,
        reference_data=True,
    )
