"""Clasificación de MRI con un motor cargado y metadatos del resultado efectivo."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.v1.dependencias import Configuracion
from app.ml.runtime import get_inference_engine
from app.repositories.cargas import RepositorioCargasDep
from app.schemas.classification import InfoModeloActivo, ResultadoClasificacion
from app.services.images import read_image

router = APIRouter(prefix="/classifications", tags=["clasificación"])
logger = logging.getLogger(__name__)


@router.get("/model-info", response_model=InfoModeloActivo)
async def info_modelo_activo(configuracion: Configuracion, request: Request) -> InfoModeloActivo:
    if configuracion.simulated_inference:
        return InfoModeloActivo(model_version="Demostración", preprocess_label="Sin modelo", simulated_inference=True)
    info = get_inference_engine(request).describe()
    return InfoModeloActivo(
        model_version=f"{info.model_name} · {info.model_version}",
        preprocess_label=info.preprocess_label, simulated_inference=info.simulated,
        model_name=info.model_name, model_uri=info.model_uri, run_id=info.run_id,
        preprocess_fingerprint=info.preprocess_fingerprint,
        supports_explanation=info.supports_explanation, evaluation_metrics=info.evaluation_metrics,
    )


@router.post("", response_model=ResultadoClasificacion, summary="Clasificar una imagen MRI")
async def clasificar_imagen(
    country_code: Annotated[str, Form(alias="countryCode")],
    configuracion: Configuracion,
    repositorio: RepositorioCargasDep,
    request: Request,
    file: Annotated[UploadFile | None, File()] = None,
    hint: Annotated[str | None, Form()] = None,
    explain: Annotated[bool, Form()] = False,
) -> ResultadoClasificacion:
    if country_code not in await repositorio.codigos_pais():
        raise HTTPException(422, "País no reconocido")
    if not configuracion.simulated_inference and hint is not None:
        raise HTTPException(422, "La clasificación real no acepta una clase sugerida")
    if file is None and not configuracion.simulated_inference:
        raise HTTPException(422, "Seleccione una imagen JPG o PNG")
    name = file.filename if file and file.filename else "demostracion.jpg"
    content = await read_image(file) if file is not None else None
    model_info = None
    started = time.perf_counter()
    if configuracion.simulated_inference:
        from app.seed.catalogos import CLASES_TUMOR
        from app.services.clasificacion import clasificar
        if hint is not None and hint not in CLASES_TUMOR:
            raise HTTPException(422, "Clase no reconocida")
        values = clasificar(country_code, pista=hint, explicar=explain,
                            version_modelo="Demostración", etiqueta_preproceso="Sin modelo")
        values["description"] = "Resultado de demostración. No se ejecutó un modelo."
    else:
        engine = get_inference_engine(request)
        model_info = engine.describe()
        try:
            async with request.app.state.inference_slots:
                results = await run_in_threadpool(
                    engine.classify, [content], explain=explain and model_info.supports_explanation,
                )
            if len(results) != 1:
                raise ValueError("El motor debe devolver exactamente una clasificación")
            prediction = results[0]
        except Exception as error:
            logger.exception("No se pudo ejecutar la inferencia")
            raise HTTPException(503, "No fue posible ejecutar el modelo. Intente nuevamente.") from error
        values = {
            "predicted_class": prediction.predicted_class,
            "confidence_by_class": {score.tumor_class: round(score.confidence * 100, 2) for score in prediction.scores},
            "description": "Clasificación del modelo. No sustituye la interpretación clínica.",
            "model_version": f"{model_info.model_name} · {model_info.model_version}",
            "preprocess": model_info.preprocess_label, "country_code": country_code,
            "model_uri": model_info.model_uri, "run_id": model_info.run_id,
            "preprocess_fingerprint": model_info.preprocess_fingerprint,
            "explanation": ({
                "method": prediction.explanation.method,
                "method_label": prediction.explanation.method_label,
                "influence_map_data_uri": prediction.explanation.data_uri,
            } if prediction.explanation else None),
        }
    elapsed = round((time.perf_counter() - started) * 1000)
    # Validar la respuesta antes de escribir: una salida inválida no deja historial.
    result = ResultadoClasificacion.model_validate({
        **values, "simulated_inference": model_info.simulated if model_info else True,
        "image_sha256": hashlib.sha256(content).hexdigest() if content else "",
    })
    try:
        upload_id = await repositorio.registrar_clasificacion(
            codigo_pais=country_code, nombre_archivo=name, contenido=content,
            clase_predicha=result.predicted_class, confianzas=result.confidence_by_class,
            etiqueta_preproceso=result.preprocess, simulada=result.simulated_inference,
            modelo_info=model_info, latencia_ms=elapsed,
        )
    except (SQLAlchemyError, ValueError) as error:
        logger.exception("No se pudo conservar la clasificación")
        raise HTTPException(503, "No se pudo guardar el resultado. La operación no se completó.") from error
    return result.model_copy(update={"upload_id": upload_id, "persisted": upload_id is not None})
