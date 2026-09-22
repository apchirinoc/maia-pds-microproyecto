"""Registro de modelos. Zona restringida."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencias import SesionRequerida
from app.ml.registry import ModeloNoVersionado, RegistroModelosDep
from app.repositories.modelos import (
    ConflictoDePromocion,
    ModeloNoEncontrado,
    RepositorioModelosDep,
)
from app.schemas.common import EsquemaBase
from app.schemas.model import (
    DetalleModelo,
    ModeloDesplegado,
    ResumenRegistroModelos,
    VersionRegistro,
)

router = APIRouter(prefix="/models", tags=["modelos"])


class RevertirEntrada(EsquemaBase):
    target_version: str


# `/summary` se declara antes que `/{model_id}`: de lo contrario el parámetro de
# ruta capturaría la palabra «summary».
@router.get("/summary", response_model=ResumenRegistroModelos, summary="Resumen del registro")
async def obtener_resumen(
    sesion: SesionRequerida, repositorio: RepositorioModelosDep
) -> ResumenRegistroModelos:
    resumen = await repositorio.obtener_resumen()
    if resumen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay ningún modelo en producción",
        )
    return ResumenRegistroModelos.model_validate(resumen)


@router.get("", response_model=list[ModeloDesplegado], summary="Modelos registrados")
async def listar_modelos(
    sesion: SesionRequerida, repositorio: RepositorioModelosDep
) -> list[ModeloDesplegado]:
    return [ModeloDesplegado.model_validate(m) for m in await repositorio.listar_modelos()]


# Rutas del registry: declaradas antes que `/{model_id}` para que el parámetro de
# ruta no capture la palabra «registry».
@router.get(
    "/registry",
    response_model=list[VersionRegistro],
    summary="Versiones disponibles en el Model Registry (S3)",
)
async def listar_registry(
    sesion: SesionRequerida, registro: RegistroModelosDep
) -> list[VersionRegistro]:
    """Lista las versiones ya versionadas en MLflow/S3, para seleccionarlas."""
    return [VersionRegistro.model_validate(version) for version in registro.listar_versiones()]


@router.post(
    "/registry/{version}/activate",
    response_model=VersionRegistro,
    summary="Activar (champion) una versión versionada en S3",
)
async def activar_registry(
    version: str, sesion: SesionRequerida, registro: RegistroModelosDep
) -> VersionRegistro:
    """Fija el alias `champion` sobre `version`: el motor de inferencia empezará a
    servir esa versión desde S3 (`models:/<name>@champion`). Sustituye al antiguo
    «subir un archivo de pesos»: aquí solo se selecciona lo ya versionado.
    """
    try:
        activada = registro.activar(version)
    except ModeloNoVersionado as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return VersionRegistro.model_validate(activada)


@router.get("/{model_id}", response_model=DetalleModelo, summary="Detalle de un modelo")
async def obtener_modelo(
    model_id: str, sesion: SesionRequerida, repositorio: RepositorioModelosDep
) -> DetalleModelo:
    detalle = await repositorio.obtener_detalle(model_id)
    if detalle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el modelo {model_id}"
        )
    return DetalleModelo.model_validate(detalle)


@router.post(
    "/{model_id}/deploy",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desplegar un modelo a producción",
)
async def desplegar(
    model_id: str, sesion: SesionRequerida, repositorio: RepositorioModelosDep
) -> None:
    try:
        await repositorio.desplegar(model_id, sesion)
    except ModeloNoEncontrado as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ConflictoDePromocion as error:
        # 409: otra promoción ganó la carrera. No es un fallo del servidor, es
        # la base impidiendo que queden dos modelos en producción.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/{model_id}/revert",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revertir a una versión anterior",
)
async def revertir(
    model_id: str,
    entrada: RevertirEntrada,
    sesion: SesionRequerida,
    repositorio: RepositorioModelosDep,
) -> None:
    try:
        await repositorio.revertir(model_id, entrada.target_version, sesion)
    except ModeloNoEncontrado as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ConflictoDePromocion as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
