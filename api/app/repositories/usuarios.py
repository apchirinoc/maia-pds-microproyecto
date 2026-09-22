"""Repositorio de usuarios: autenticación contra el origen de datos activo.

Sigue el mismo patrón que `repositories/catalogos.py`:

  1. Un `Protocol` que define el contrato de autenticación.
  2. `UsuariosSeed`, que valida contra la cuenta de demostración del `.env`.
  3. `UsuariosPostgres`, que valida contra la tabla `users` con Argon2id.
  4. Una dependencia que elige según `DATA_SOURCE`.

El router de autenticación depende del `Protocol`: conectar la base no cambia
el contrato de `/auth/login` ni el contenido del token, sólo el sitio de donde
salen la identidad y el rol.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencias import Configuracion
from app.core.security import hash_password, verify_password
from app.db.session import get_session_opcional
from app.models.entidades import User
from app.schemas.auth import SesionAdmin

# Sesión que devuelve el modo `seed`: el prototipo se demuestra con esta cuenta
# y su identidad coincide con la que siembra `dml/02_usuarios.sql`.
SESION_DEMO = SesionAdmin(username="m.rivera", display_name="M. Rivera", role="Admin")


@lru_cache(maxsize=1)
def _hash_senuelo() -> str:
    """Hash de descarte para verificar incluso cuando el usuario no existe.

    Sin esto, un usuario inexistente responde mucho antes que uno existente con
    contraseña incorrecta, y esa diferencia de tiempo permite enumerar cuentas.
    Se calcula una sola vez porque Argon2id es deliberadamente costoso.
    """
    return hash_password("contrasena-que-nadie-tiene")


class RepositorioUsuarios(Protocol):
    async def autenticar(self, usuario: str, contrasena: str) -> SesionAdmin | None:
        """Devuelve la sesión si las credenciales son válidas, o None."""
        ...


class UsuariosSeed(RepositorioUsuarios):
    """Valida contra la cuenta de demostración declarada en el entorno."""

    def __init__(self, configuracion) -> None:
        self._configuracion = configuracion

    async def autenticar(self, usuario: str, contrasena: str) -> SesionAdmin | None:
        valido = (
            usuario.strip() == self._configuracion.demo_username
            and contrasena == self._configuracion.demo_password
        )
        return SESION_DEMO if valido else None


class UsuariosPostgres(RepositorioUsuarios):
    """Valida contra la tabla `users` y anota el ingreso en `last_login_at`."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def autenticar(self, usuario: str, contrasena: str) -> SesionAdmin | None:
        # `username` es citext en el esquema: la comparación ya es insensible a
        # mayúsculas y aprovecha el índice único de la columna.
        fila = await self._sesion.scalar(select(User).where(User.username == usuario.strip()))

        if fila is None:
            # Se verifica igualmente contra el señuelo para no delatar por
            # tiempo de respuesta que la cuenta no existe.
            verify_password(contrasena, _hash_senuelo())
            return None

        # Cuenta desactivada o dada de baja lógica: no autentica aunque la
        # contraseña sea correcta. Se comprueba antes de verificar el hash para
        # no gastar el coste de Argon2id en una cuenta que no puede entrar.
        if not fila.is_active or fila.deleted_at is not None:
            return None

        if not verify_password(contrasena, fila.hashed_password):
            return None

        # El commit lo hace `get_session_opcional` al cerrar la petición.
        fila.last_login_at = datetime.now(timezone.utc)

        return SesionAdmin(
            username=fila.username,
            display_name=fila.display_name,
            # El rol es el nombre legible del catálogo `roles`, no el código.
            role=fila.role.name,
        )


def obtener_repositorio_usuarios(
    configuracion: Configuracion,
    sesion: Annotated[AsyncSession | None, Depends(get_session_opcional)],
) -> RepositorioUsuarios:
    """`sesion` llega como None cuando DATA_SOURCE no es postgres."""
    return UsuariosSeed(configuracion) if sesion is None else UsuariosPostgres(sesion)


RepositorioUsuariosDep = Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)]
