"""Utilidades compartidas por las pruebas del API.

Las pruebas se ejecutan contra los **dos orígenes de datos**: `seed` (memoria)
y `postgres`. Es el único modo de detectar que conectar la base cambia el
contrato, que es justo el fallo que estas pruebas existen para impedir.

Si no hay PostgreSQL disponible, las pruebas del modo `postgres` se omiten en
lugar de fallar: la plataforma debe poder desarrollarse sin base de datos.
"""

from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ORIGENES = ("seed", "postgres")


def _hay_postgres() -> bool:
    """Comprueba que el puerto de PostgreSQL acepta conexiones."""
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


HAY_POSTGRES = _hay_postgres()

requiere_postgres = pytest.mark.skipif(
    not HAY_POSTGRES,
    reason="No hay PostgreSQL escuchando en 127.0.0.1:5432 (levántalo con «cd model && docker compose up -d»)",
)


def construir_app(origen: str):
    """Crea una aplicación con el origen de datos indicado.

    `get_settings` está memoizada y `get_engine` también: hay que limpiar
    ambas cachés para que el cambio de `DATA_SOURCE` surta efecto, o la segunda
    aplicación reutilizaría la configuración de la primera.
    """
    os.environ["DATA_SOURCE"] = origen

    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    from app.main import crear_app

    return crear_app()


@pytest.fixture(params=ORIGENES, ids=ORIGENES)
def origen(request: pytest.FixtureRequest) -> Iterator[str]:
    """Parametriza cada prueba sobre los dos orígenes de datos."""
    if request.param == "postgres" and not HAY_POSTGRES:
        pytest.skip("PostgreSQL no está disponible")
    yield request.param


@pytest_asyncio.fixture
async def cliente(origen: str) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP contra la aplicación, sin levantar un servidor real."""
    app = construir_app(origen)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://pruebas"
    ) as cliente:
        yield cliente


@pytest_asyncio.fixture
async def cliente_seed() -> AsyncIterator[AsyncClient]:
    app = construir_app("seed")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://pruebas"
    ) as cliente:
        yield cliente


@pytest_asyncio.fixture
async def token(cliente: AsyncClient) -> str:
    """Token de acceso de la cuenta de demostración."""
    respuesta = await cliente.post(
        "/api/v1/auth/login", json={"username": "demo", "password": "demo"}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["accessToken"]


@pytest_asyncio.fixture
async def cabeceras(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
