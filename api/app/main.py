"""Punto de entrada de la API de BrainNeuroScan.

Publica OpenAPI 3.1 en `/openapi.json`, Swagger en `/docs` y ReDoc en `/redoc`.
El contrato que aquí se declara es el que el frontend consume: los esquemas se
serializan en `camelCase` para encajar con sus tipos sin adaptadores.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as router_v1
from app.core.config import get_settings
from app.ml.runtime import lifespan

DESCRIPCION = """
API de **BrainNeuroScan**, plataforma de investigación para clasificación de
tumores cerebrales por MRI.

⚠️ Prototipo de investigación. No es un dispositivo médico y no cuenta con
certificaciones vigentes. La inferencia está simulada mientras
`INFERENCE_ENGINE=simulated`.
"""


def crear_app() -> FastAPI:
    configuracion = get_settings()

    app = FastAPI(
        title=configuracion.app_name,
        description=DESCRIPCION,
        version=configuracion.api_version.lstrip("v"),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    cors_origins = configuracion.origins
    cors_kwargs: dict = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Process-Time-Ms"],
    }
    if "*" in cors_origins:
        cors_kwargs["allow_origins"] = []
        cors_kwargs["allow_origin_regex"] = ".*"
    else:
        cors_kwargs["allow_origins"] = cors_origins

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    @app.middleware("http")
    async def medir_latencia(request: Request, call_next):
        inicio = time.perf_counter()
        respuesta = await call_next(request)
        transcurrido = (time.perf_counter() - inicio) * 1000
        respuesta.headers["X-Process-Time-Ms"] = f"{transcurrido:.1f}"
        return respuesta

    def problema(status_code: int, title: str, detail: str | None, request: Request):
        """Errores normalizados según RFC 7807."""
        return JSONResponse(
            status_code=status_code,
            content={
                "type": "about:blank",
                "title": title,
                "status": status_code,
                "detail": detail,
                "instance": str(request.url.path),
            },
            media_type="application/problem+json",
        )

    @app.exception_handler(StarletteHTTPException)
    async def manejar_http(request: Request, exc: StarletteHTTPException):
        return problema(exc.status_code, "Error de solicitud", str(exc.detail), request)

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(request: Request, exc: RequestValidationError):
        return problema(422, "Solicitud inválida", str(exc.errors()), request)

    @app.exception_handler(Exception)
    async def manejar_error_inesperado(request: Request, exc: Exception):
        return problema(
            500,
            "Error interno del servidor",
            str(exc) if configuracion.debug else "Ocurrió un error inesperado en el servidor",
            request,
        )

    @app.get("/health", tags=["meta"], summary="Sonda de salud")
    def salud() -> dict[str, str]:
        """Sonda que el frontend usa para decidir si hay backend disponible.

        Es deliberadamente barata y sin autenticación: se consulta en cada
        arranque de la interfaz y de forma periódica.
        """
        return {"status": "ok", "service": configuracion.app_name}

    app.include_router(router_v1)

    @app.get("/ready", tags=["meta"], summary="Disponibilidad del modelo y almacenamiento")
    async def disponibilidad(request: Request):
        if configuracion.inference_engine == "onnx" and getattr(request.app.state, "inference_engine", None) is None:
            return JSONResponse({"status": "unavailable", "modelReady": False}, status_code=503)
        if configuracion.data_source == "postgres":
            from sqlalchemy import text
            from app.db.session import get_sessionmaker
            try:
                async with get_sessionmaker()() as session:
                    await session.execute(text("SELECT 1"))
            except Exception:
                return JSONResponse({"status": "unavailable", "storageReady": False}, status_code=503)
        return {"status": "ok", "simulatedInference": configuracion.simulated_inference}

    return app


app = crear_app()
