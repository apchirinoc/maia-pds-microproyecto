"""El contrato debe ser idéntico con datos simulados y con PostgreSQL.

Conectar la base puede cambiar los **valores**, nunca la **forma** de la
respuesta. Si cambiara, el frontend se rompería sólo en producción, que es
donde peor se descubre.

Qué protege exactamente, comprobado con controles negativos:

* **Un campo que falte** en uno de los dos caminos: sí se detecta. Pydantic
  rechaza la respuesta y el endpoint devuelve 500 en ese modo.
* **Un campo de más** en uno de los caminos: NO se detecta aquí, y no hace
  falta. El `response_model` de cada endpoint descarta las claves que no
  declara, así que un repositorio no puede filtrar campos al cliente por
  descuido. Esa mitad la garantiza el framework, no esta prueba.

El valor real, entonces, es doble: verifica que **cada endpoint responde en
ambos modos** y que ningún repositorio se deja un campo obligatorio.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import construir_app, requiere_postgres

PUBLICOS = (
    "/health",
    "/api/v1/meta",
    "/api/v1/countries",
    "/api/v1/dashboard/kpis",
    "/api/v1/dashboard/training-distribution",
    "/api/v1/dashboard/uploads-by-country",
    "/api/v1/dashboard/uploads-by-month",
    "/api/v1/dashboard/recent-profile",
    "/api/v1/dashboard/dataset-samples",
    "/api/v1/classifications/model-info",
)

PROTEGIDOS = (
    "/api/v1/models",
    "/api/v1/models/summary",
    "/api/v1/models/effnetb3-bt-v2.4",
    "/api/v1/uploads?page=1&pageSize=3",
    "/api/v1/uploads/summary",
)


def _forma(valor: object, prefijo: str = "") -> set[str]:
    """Conjunto de rutas de claves, ignorando los valores.

    De una lista se recorren **todos** los elementos y se unen sus formas. Mirar
    sólo el primero daba falsos positivos: si su `groundTruth` era `null` —cosa
    legítima— las claves anidadas no aparecían, y la comparación denunciaba una
    divergencia que no existía.
    """
    if isinstance(valor, dict):
        rutas: set[str] = set()
        for clave, contenido in valor.items():
            ruta = f"{prefijo}.{clave}" if prefijo else str(clave)
            rutas.add(ruta)
            rutas |= _forma(contenido, ruta)
        return rutas
    if isinstance(valor, list):
        rutas = set()
        for elemento in valor:
            rutas |= _forma(elemento, f"{prefijo}[]")
        return rutas
    return set()


@pytest.mark.parametrize("ruta", PUBLICOS)
async def test_endpoint_publico_responde(cliente: AsyncClient, ruta: str) -> None:
    respuesta = await cliente.get(ruta)
    assert respuesta.status_code == 200, respuesta.text


@pytest.mark.parametrize("ruta", PROTEGIDOS)
async def test_endpoint_protegido_responde(
    cliente: AsyncClient, cabeceras: dict[str, str], ruta: str
) -> None:
    respuesta = await cliente.get(ruta, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text


async def _respuestas(rutas: tuple[str, ...], autenticado: bool) -> dict[str, dict[str, set[str]]]:
    from httpx import ASGITransport, AsyncClient as Cliente

    formas: dict[str, dict[str, set[str]]] = {ruta: {} for ruta in rutas}
    for origen in ("seed", "postgres"):
        app = construir_app(origen)
        async with Cliente(transport=ASGITransport(app=app), base_url="http://pruebas") as c:
            cabeceras: dict[str, str] = {}
            if autenticado:
                acceso = await c.post(
                    "/api/v1/auth/login", json={"username": "demo", "password": "demo"}
                )
                assert acceso.status_code == 200, f"{origen}: {acceso.text}"
                cabeceras = {"Authorization": f"Bearer {acceso.json()['accessToken']}"}
            for ruta in rutas:
                respuesta = await c.get(ruta, headers=cabeceras)
                assert respuesta.status_code == 200, f"{origen} {ruta}: {respuesta.text}"
                formas[ruta][origen] = _forma(respuesta.json())
    return formas


@requiere_postgres
async def test_los_endpoints_publicos_tienen_la_misma_forma_en_ambos_origenes() -> None:
    for ruta, formas in (await _respuestas(PUBLICOS, autenticado=False)).items():
        assert formas["seed"] == formas["postgres"], (
            f"{ruta} cambia de forma al conectar la base. "
            f"Sólo en semilla: {sorted(formas['seed'] - formas['postgres'])}. "
            f"Sólo en postgres: {sorted(formas['postgres'] - formas['seed'])}."
        )


@requiere_postgres
async def test_los_endpoints_protegidos_tienen_la_misma_forma_en_ambos_origenes() -> None:
    for ruta, formas in (await _respuestas(PROTEGIDOS, autenticado=True)).items():
        assert formas["seed"] == formas["postgres"], (
            f"{ruta} cambia de forma al conectar la base. "
            f"Sólo en semilla: {sorted(formas['seed'] - formas['postgres'])}. "
            f"Sólo en postgres: {sorted(formas['postgres'] - formas['seed'])}."
        )
