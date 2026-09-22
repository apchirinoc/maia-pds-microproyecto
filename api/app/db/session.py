"""Motor asíncrono y sesión de base de datos."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Motor único del proceso.

    `pool_pre_ping` evita servir una conexión que el servidor ya cerró, que es
    el fallo típico tras un reinicio de la base o un corte de red.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: una sesión por petición.

    Confirma al terminar bien y revierte ante cualquier excepción, de modo que
    ninguna petición pueda dejar una transacción a medias.
    """
    async with get_sessionmaker()() as sesion:
        try:
            yield sesion
            await sesion.commit()
        except Exception:
            await sesion.rollback()
            raise


async def get_session_opcional() -> AsyncGenerator[AsyncSession | None, None]:
    """Sesión sólo cuando el origen de datos es PostgreSQL.

    Con `DATA_SOURCE=seed` devuelve `None` sin abrir conexión: la plataforma
    debe arrancar sin base de datos. Es una dependencia de FastAPI y no un
    generador consumido a mano, para que el commit y el cierre ocurran al
    terminar la petición y no cuando el recolector de basura pase por ahí.
    """
    if get_settings().data_source != "postgres":
        yield None
        return

    async with get_sessionmaker()() as sesion:
        try:
            yield sesion
            await sesion.commit()
        except Exception:
            await sesion.rollback()
            raise
