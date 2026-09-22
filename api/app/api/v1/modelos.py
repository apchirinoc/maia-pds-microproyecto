"""Registro de modelos. Zona restringida."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencias import SesionRequerida
from app.repositories.modelos import (
    ConflictoDePromocion,
    ModeloNoEncontrado,
    RepositorioModelosDep,
)
from app.schemas.common import EsquemaBase
from app.schemas.model import DetalleModelo, ModeloDesplegado, ResumenRegistroModelos

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
