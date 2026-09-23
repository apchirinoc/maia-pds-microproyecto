"""Clasificación de imágenes MRI. Endpoint público."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.v1.dependencias import Configuracion
from app.api.v1.meta import ETIQUETA_PREPROCESO
from app.ml.proveedor import MotorInferenciaDep
from app.repositories.cargas import RepositorioCargasDep
from app.schemas.classification import InfoModeloActivo, ResultadoClasificacion
from app.seed.catalogos import CLASES_TUMOR
from app.services.clasificacion import clasificar, clasificar_con_motor

router = APIRouter(prefix="/classifications", tags=["clasificación"])

TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024
TIPOS_ACEPTADOS = {"image/jpeg", "image/png"}


@router.get("/model-info", response_model=InfoModeloActivo, summary="Modelo que está sirviendo")
async def info_modelo_activo(
    repositorio: RepositorioCargasDep, motor: MotorInferenciaDep
) -> InfoModeloActivo:
    if motor is not None:
        info = motor.describe()
        return InfoModeloActivo(
            model_version=info.model_version,
            preprocess_label=info.preprocess_label,
            simulated_inference=False,
        )
    return InfoModeloActivo(
        model_version=await repositorio.version_modelo_produccion(),
        preprocess_label=ETIQUETA_PREPROCESO,
        simulated_inference=True,
    )


@router.post("", response_model=ResultadoClasificacion, summary="Clasificar una imagen MRI")
async def clasificar_imagen(
    country_code: Annotated[str, Form(alias="countryCode")],
    configuracion: Configuracion,
    repositorio: RepositorioCargasDep,
    motor: MotorInferenciaDep,
    file: Annotated[UploadFile | None, File()] = None,
    hint: Annotated[str | None, Form()] = None,
    explain: Annotated[bool, Form()] = True,
) -> ResultadoClasificacion:
    if country_code not in await repositorio.codigos_pais():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"País no reconocido: {country_code}",
        )

    contenido: bytes | None = None
    nombre_archivo = "muestra-dataset.jpg"
    if file is not None:
        if file.content_type not in TIPOS_ACEPTADOS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Sólo se aceptan imágenes JPG o PNG",
            )
        contenido = await file.read()
        if len(contenido) > TAMANO_MAXIMO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="La imagen supera los 8 MB",
            )
        nombre_archivo = file.filename or nombre_archivo

    if hint is not None and hint not in CLASES_TUMOR:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Clase no reconocida: {hint}",
        )

    if motor is not None:
        if contenido is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La inferencia real necesita el archivo de la imagen",
            )
        # `hint` solo sirve para forzar la clase en la simulación: aquí se ignora.
        resultado = await run_in_threadpool(
            clasificar_con_motor, motor, contenido, country_code, explicar=explain
        )
    else:
        resultado = clasificar(
            country_code,
            pista=hint,
            explicar=explain,
            version_modelo=await repositorio.version_modelo_produccion(),
            etiqueta_preproceso=ETIQUETA_PREPROCESO,
        )

    # La inferencia la produce el servicio; el repositorio sólo la persiste.
    await repositorio.registrar_clasificacion(
        codigo_pais=country_code,
        nombre_archivo=nombre_archivo,
        contenido=contenido,
        clase_predicha=resultado["predicted_class"],
        confianzas=resultado["confidence_by_class"],
        etiqueta_preproceso=resultado["preprocess"],
        simulada=configuracion.simulated_inference,
    )

    return ResultadoClasificacion.model_validate(resultado)
