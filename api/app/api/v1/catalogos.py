"""Catálogos públicos."""

from __future__ import annotations

from fastapi import APIRouter

from app.repositories.catalogos import RepositorioCatalogosDep
from app.schemas.dashboard import Pais

router = APIRouter(tags=["catálogos"])


@router.get("/countries", response_model=list[Pais], summary="Países disponibles")
async def listar_paises(repositorio: RepositorioCatalogosDep) -> list[Pais]:
    return [Pais.model_validate(pais) for pais in await repositorio.listar_paises()]
