"""Autenticación y control de acceso."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

RUTAS_PROTEGIDAS = (
    "/api/v1/models",
    "/api/v1/models/summary",
    "/api/v1/uploads",
    "/api/v1/uploads/summary",
)


async def test_credenciales_validas_devuelven_sesion_y_token(cliente: AsyncClient) -> None:
    respuesta = await cliente.post(
        "/api/v1/auth/login", json={"username": "demo", "password": "demo"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["session"]["role"]
    assert cuerpo["tokenType"] == "bearer"
    assert cuerpo["expiresInSeconds"] > 0
    assert cuerpo["accessToken"].count(".") == 2  # cabecera.carga.firma


@pytest.mark.parametrize(
    "credenciales",
    [
        {"username": "demo", "password": "incorrecta"},
        {"username": "intruso", "password": "demo"},
    ],
    ids=["contraseña incorrecta", "usuario inexistente"],
)
async def test_credenciales_invalidas_son_rechazadas(
    cliente: AsyncClient, credenciales: dict[str, str]
) -> None:
    respuesta = await cliente.post("/api/v1/auth/login", json=credenciales)
    assert respuesta.status_code == 401


async def test_credenciales_vacias_no_llegan_al_repositorio(cliente: AsyncClient) -> None:
    """El esquema exige longitud mínima: se rechaza antes de consultar nada."""
    respuesta = await cliente.post("/api/v1/auth/login", json={"username": "", "password": ""})
    assert respuesta.status_code == 422


@pytest.mark.parametrize("ruta", RUTAS_PROTEGIDAS)
async def test_zona_restringida_exige_token(cliente: AsyncClient, ruta: str) -> None:
    assert (await cliente.get(ruta)).status_code == 401


@pytest.mark.parametrize("ruta", RUTAS_PROTEGIDAS)
async def test_zona_restringida_acepta_token_valido(
    cliente: AsyncClient, cabeceras: dict[str, str], ruta: str
) -> None:
    assert (await cliente.get(ruta, headers=cabeceras)).status_code == 200


async def test_token_manipulado_es_rechazado(cliente: AsyncClient, token: str) -> None:
    """Alterar la carga invalida la firma: es lo que impide falsificar un rol."""
    cabecera, carga, firma = token.split(".")
    manipulado = f"{cabecera}.{carga[:-4]}AAAA.{firma}"
    respuesta = await cliente.get(
        "/api/v1/models", headers={"Authorization": f"Bearer {manipulado}"}
    )
    assert respuesta.status_code == 401


async def test_sesion_actual_refleja_al_usuario(
    cliente: AsyncClient, cabeceras: dict[str, str]
) -> None:
    respuesta = await cliente.get("/api/v1/auth/me", headers=cabeceras)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"username", "displayName", "role"}
