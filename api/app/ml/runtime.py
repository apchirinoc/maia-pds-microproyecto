"""Una instancia del motor por proceso, cargada antes de aceptar inferencias."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.ml.engine import InferenceEngine


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    app.state.inference_engine = None
    app.state.inference_slots = asyncio.Semaphore(settings.inference_concurrency)
    if settings.inference_engine == "onnx":
        from app.ml.mlflow_engine import MlflowInferenceEngine

        # Un fallo de carga aborta el arranque. Nunca se sustituye por simulación.
        app.state.inference_engine = await run_in_threadpool(
            MlflowInferenceEngine,
            settings.mlflow_model_name,
            alias=settings.mlflow_model_alias,
            version=settings.mlflow_model_version or None,
            model_uri=settings.mlflow_model_uri or None,
            tracking_uri=settings.mlflow_tracking_uri or None,
            expected_preprocess_fingerprint=settings.expected_preprocess_fingerprint or None,
        )
        if settings.data_source == "postgres":
            from app.db.session import get_sessionmaker
            from app.services.model_catalog import serving_model
            async with get_sessionmaker()() as session:
                await serving_model(session, app.state.inference_engine.describe())
                await session.commit()
    try:
        yield
    finally:
        app.state.inference_engine = None


def get_inference_engine(request: Request) -> InferenceEngine:
    engine = getattr(request.app.state, "inference_engine", None)
    if engine is None:
        raise HTTPException(503, "El modelo de inferencia no está disponible")
    return engine


MotorDep = Annotated[InferenceEngine, Depends(get_inference_engine)]
