"""Autenticación.

El router no sabe contra qué valida: delega en `RepositorioUsuarios`, que con
`DATA_SOURCE=seed` compara con la cuenta del `.env` y con `DATA_SOURCE=postgres`
consulta la tabla `users`. El token emitido lleva las mismas reclamaciones en
ambos casos (`displayName` y `role`), de modo que `GET /auth/me` responde igual
sin importar el origen de datos.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencias import Configuracion, SesionRequerida
from app.core.security import create_access_token
from app.repositories.usuarios import RepositorioUsuariosDep
from app.schemas.auth import CredencialesEntrada, RespuestaSesion, SesionAdmin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=RespuestaSesion, summary="Iniciar sesión")
async def iniciar_sesion(
    credenciales: CredencialesEntrada,
    configuracion: Configuracion,
    usuarios: RepositorioUsuariosDep,
) -> RespuestaSesion:
    sesion = await usuarios.autenticar(credenciales.username, credenciales.password)
    if sesion is None:
        # Un único mensaje para credenciales erróneas, cuenta inexistente,
        # cuenta desactivada y cuenta dada de baja: distinguirlos permitiría
        # enumerar usuarios válidos desde fuera.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    token = create_access_token(
        sesion.username,
        claims={"displayName": sesion.display_name, "role": sesion.role},
    )
    return RespuestaSesion(
        session=sesion,
        access_token=token,
        expires_in_seconds=configuracion.access_token_ttl_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def cerrar_sesion() -> None:
    """El token es sin estado: la sesión se descarta en el cliente.

    Cuando exista `refresh_tokens` en Postgres (§10.3), aquí se revoca.
    """
    return None


@router.get("/me", response_model=SesionAdmin, summary="Sesión actual")
def sesion_actual(sesion: SesionRequerida) -> SesionAdmin:
    return sesion
