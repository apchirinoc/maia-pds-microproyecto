"""Repositorio de catálogos — implementación de referencia.

Patrón que siguen todos los repositorios del API:

  1. Un `Protocol` que define el contrato, sin saber de dónde salen los datos.
  2. Una implementación `...Seed` que lee de `app/seed/` (memoria).
  3. Una implementación `...Postgres` que consulta la base con SQLAlchemy.
  4. Una dependencia que elige según `DATA_SOURCE`.

Los routers dependen del `Protocol`, nunca de una implementación concreta. Así
la plataforma sigue arrancando sin base de datos —que es lo que sostiene la
demostración con datos simulados— y la conmutación es una variable de entorno.
"""

from __future__ import annotations

from typing import Annotated, Any, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_opcional
from app.models.entidades import Country
from app.seed.catalogos import PAISES


class RepositorioCatalogos(Protocol):
    async def listar_paises(self) -> list[dict[str, Any]]: ...


class CatalogosSeed(RepositorioCatalogos):
    async def listar_paises(self) -> list[dict[str, Any]]:
        return list(PAISES)


class CatalogosPostgres(RepositorioCatalogos):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar_paises(self) -> list[dict[str, Any]]:
        filas = await self._sesion.scalars(select(Country).order_by(Country.name))
        return [
            {
                "code": pais.code,
                "name": pais.name,
                # Los decimales de Postgres se convierten aquí: el esquema de
                # salida declara float y Pydantic no debe recibir Decimal.
                "latitude": float(pais.latitude),
                "longitude": float(pais.longitude),
            }
            for pais in filas
        ]


def obtener_repositorio_catalogos(
    sesion: Annotated[AsyncSession | None, Depends(get_session_opcional)],
) -> RepositorioCatalogos:
    """`sesion` llega como None cuando DATA_SOURCE no es postgres."""
    return CatalogosSeed() if sesion is None else CatalogosPostgres(sesion)


RepositorioCatalogosDep = Annotated[RepositorioCatalogos, Depends(obtener_repositorio_catalogos)]
