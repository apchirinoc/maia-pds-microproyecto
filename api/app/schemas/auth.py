"""Esquemas de autenticación."""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import EsquemaBase


class CredencialesEntrada(EsquemaBase):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class SesionAdmin(EsquemaBase):
    username: str
    display_name: str
    role: str


class RespuestaSesion(EsquemaBase):
    """La sesión que consume `useAuth`, con el token de acceso."""

    session: SesionAdmin
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
