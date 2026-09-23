"""Panel analítico. Todos los endpoints son públicos, como la vista.

El router no sabe si los datos vienen de PostgreSQL o de la semilla en memoria:
depende del `RepositorioPanel`, que se resuelve según `DATA_SOURCE`. La forma de
la respuesta es idéntica en ambos modos; sólo cambian los valores.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from app.core.config import get_settings

from app.repositories.panel import RepositorioPanelDep
from app.schemas.dashboard import (
    CargasPorMes,
    CargasPorPais,
    DashboardKpis,
    DistribucionPorClase,
    MuestraDataset,
    PerfilCargasRecientes,
)

router = APIRouter(prefix="/dashboard", tags=["panel"])


@router.get("/kpis", response_model=DashboardKpis, summary="Indicadores del panel")
async def obtener_kpis(repositorio: RepositorioPanelDep, request: Request) -> DashboardKpis:
    values = await repositorio.obtener_kpis()
    engine = getattr(request.app.state, "inference_engine", None)
    if not get_settings().simulated_inference:
        accuracy = engine.describe().evaluation_metrics.get("test_accuracy") if engine else None
        values.update(
            model_accuracy=accuracy * 100 if accuracy is not None else None,
            model_accuracy_delta_pts=None,
            model_accuracy_source="model" if accuracy is not None else "unavailable",
        )
    return DashboardKpis.model_validate(values)


@router.get(
    "/training-distribution",
    response_model=DistribucionPorClase,
    summary="Distribución del dataset por clase",
)
async def obtener_distribucion(repositorio: RepositorioPanelDep) -> DistribucionPorClase:
    return DistribucionPorClase.model_validate(await repositorio.obtener_distribucion())


@router.get(
    "/uploads-by-country", response_model=list[CargasPorPais], summary="Cargas por país"
)
async def obtener_cargas_por_pais(repositorio: RepositorioPanelDep) -> list[CargasPorPais]:
    return [
        CargasPorPais.model_validate(fila)
        for fila in await repositorio.listar_cargas_por_pais()
    ]


@router.get("/uploads-by-month", response_model=list[CargasPorMes], summary="Cargas por mes")
async def obtener_cargas_por_mes(repositorio: RepositorioPanelDep) -> list[CargasPorMes]:
    return [
        CargasPorMes.model_validate(fila) for fila in await repositorio.listar_cargas_por_mes()
    ]


@router.get(
    "/recent-profile",
    response_model=list[PerfilCargasRecientes],
    summary="Perfil de cargas recientes",
)
async def obtener_perfil(repositorio: RepositorioPanelDep) -> list[PerfilCargasRecientes]:
    return [
        PerfilCargasRecientes.model_validate(fila)
        for fila in await repositorio.obtener_perfil_reciente()
    ]


@router.get(
    "/dataset-samples", response_model=list[MuestraDataset], summary="Muestras del dataset"
)
async def obtener_muestras(repositorio: RepositorioPanelDep) -> list[MuestraDataset]:
    return [
        MuestraDataset.model_validate(fila)
        for fila in await repositorio.listar_muestras_dataset()
    ]
