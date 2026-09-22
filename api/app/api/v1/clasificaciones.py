"""Clasificación de imágenes MRI. Endpoint público."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.v1.dependencias import Configuracion
from app.api.v1.meta import ETIQUETA_PREPROCESO
from app.repositories.cargas import RepositorioCargasDep
from app.schemas.classification import InfoModeloActivo, ResultadoClasificacion
from app.seed.catalogos import CLASES_TUMOR
from app.services.clasificacion import clasificar

router = APIRouter(prefix="/classifications", tags=["clasificación"])

TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024
TIPOS_ACEPTADOS = {"image/jpeg", "image/png"}


@router.get("/model-info", response_model=InfoModeloActivo, summary="Modelo que está sirviendo")
async def info_modelo_activo(
    configuracion: Configuracion, repositorio: RepositorioCargasDep
) -> InfoModeloActivo:
    return InfoModeloActivo(
        model_version=await repositorio.version_modelo_produccion(),
        preprocess_label=ETIQUETA_PREPROCESO,
        simulated_inference=configuracion.simulated_inference,
    )


@router.post("", response_model=ResultadoClasificacion, summary="Clasificar una imagen MRI")
async def clasificar_imagen(
    country_code: Annotated[str, Form(alias="countryCode")],
    configuracion: Configuracion,
    repositorio: RepositorioCargasDep,
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

    version_modelo = await repositorio.version_modelo_produccion()
    resultado = clasificar(
        country_code,
        pista=hint,
        explicar=explain,
        version_modelo=version_modelo,
        etiqueta_preproceso=ETIQUETA_PREPROCESO,
    )

    # La inferencia la produce el servicio; el repositorio sólo la persiste.
    await repositorio.registrar_clasificacion(
        codigo_pais=country_code,
        nombre_archivo=nombre_archivo,
        contenido=contenido,
        clase_predicha=resultado["predicted_class"],
        confianzas=resultado["confidence_by_class"],
        etiqueta_preproceso=ETIQUETA_PREPROCESO,
        simulada=configuracion.simulated_inference,
    )

    return ResultadoClasificacion.model_validate(resultado)
