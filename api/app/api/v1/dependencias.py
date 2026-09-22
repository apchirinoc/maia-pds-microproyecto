"""Dependencias compartidas por los routers."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.schemas.auth import SesionAdmin

_esquema_bearer = HTTPBearer(auto_error=False)

Configuracion = Annotated[Settings, Depends(get_settings)]


def obtener_sesion(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
) -> SesionAdmin:
    """Valida el token y devuelve la sesión administrativa."""
    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de acceso",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        contenido = decode_access_token(credenciales.credentials)
    except jwt.ExpiredSignatureError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="El token ha expirado"
        ) from error
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        ) from error

    return SesionAdmin(
        username=contenido["sub"],
        display_name=contenido.get("displayName", contenido["sub"]),
        role=contenido.get("role", "Admin"),
    )


SesionRequerida = Annotated[SesionAdmin, Depends(obtener_sesion)]
