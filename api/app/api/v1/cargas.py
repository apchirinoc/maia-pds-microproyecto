"""Histórico de cargas y circuito de verdad de campo. Zona restringida."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.dependencias import SesionRequerida
from app.repositories.cargas import RepositorioCargasDep
from app.schemas.common import ResultadoPaginado
from app.schemas.upload import (
    RegistrarVerdadCampoEntrada,
    RegistroCarga,
    ResumenHistorico,
)

router = APIRouter(prefix="/uploads", tags=["cargas"])

ClaseFiltro = Literal["all", "glioma", "meningioma", "pituitary", "healthy"]


@router.get("/summary", response_model=ResumenHistorico, summary="Resumen del histórico")
async def obtener_resumen(
    sesion: SesionRequerida, repositorio: RepositorioCargasDep
) -> ResumenHistorico:
    return ResumenHistorico.model_validate(await repositorio.obtener_resumen())


@router.get("/export", summary="Exportar el histórico en CSV")
async def exportar_csv(
    sesion: SesionRequerida, repositorio: RepositorioCargasDep
) -> StreamingResponse:
    return StreamingResponse(
        repositorio.exportar_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="brainneuroscan-upload-history.csv"'
        },
    )


@router.post("/add-to-dataset", status_code=status.HTTP_202_ACCEPTED, summary="Añadir al dataset")
async def anadir_al_dataset(
    ids: list[str], sesion: SesionRequerida, repositorio: RepositorioCargasDep
) -> dict[str, int]:
    return {"accepted": await repositorio.anadir_al_dataset(ids)}


@router.get("", response_model=ResultadoPaginado[RegistroCarga], summary="Histórico paginado")
async def listar_cargas(
    sesion: SesionRequerida,
    repositorio: RepositorioCargasDep,
    tumor_class: ClaseFiltro = Query(default="all", alias="tumorClass"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=100, alias="pageSize"),
) -> ResultadoPaginado[RegistroCarga]:
    registros, total = await repositorio.listar_cargas(
        clase=tumor_class, pagina=page, tamano_pagina=page_size
    )
    return ResultadoPaginado[RegistroCarga](
        items=[RegistroCarga.model_validate(r) for r in registros],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{upload_id}/ground-truth",
    response_model=RegistroCarga,
    summary="Registrar el diagnóstico confirmado",
)
async def registrar_verdad_campo(
    upload_id: str,
    entrada: RegistrarVerdadCampoEntrada,
    sesion: SesionRequerida,
    repositorio: RepositorioCargasDep,
) -> RegistroCarga:
    """Sustituye la confirmación vigente, igual que impone el índice único
    parcial `uq_ground_truth_vigente_por_carga`."""
    registro = await repositorio.registrar_verdad_campo(
        upload_id,
        diagnostico=entrada.diagnosis,
        confirmado_por=entrada.confirmed_by,
        fuente=entrada.source,
    )
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe la carga {upload_id}"
        )
    return RegistroCarga.model_validate(registro)
