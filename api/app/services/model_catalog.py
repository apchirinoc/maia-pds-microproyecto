"""Relaciona cada inferencia con una identidad inmutable, sin métricas inventadas."""
import hashlib
import uuid
from datetime import date

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.engine import ModelInfo
from app.models.entidades import Model


async def serving_model(session: AsyncSession, info: ModelInfo) -> Model:
    # Serializa altas del catálogo entre solicitudes y workers de la misma API.
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('brainneuroscan:model'))"))
    identity = f"{info.model_name}:{info.model_version}"
    slug = "model-" + hashlib.sha256(identity.encode()).hexdigest()[:24]
    model = await session.scalar(select(Model).where(Model.slug == slug))
    if model is not None:
        if model.weights_sha256 and info.weights_sha256 and model.weights_sha256 != info.weights_sha256:
            raise ValueError("Una versión de modelo no puede cambiar de pesos")
        await session.execute(update(Model).where(Model.status == "production", Model.id != model.id).values(status="archived"))
        model.status = "production"
        return model
    metrics = info.evaluation_metrics
    await session.execute(update(Model).where(Model.status == "production").values(status="archived"))
    model = Model(
        id=uuid.uuid4(), slug=slug, name=info.model_name, version=info.model_version,
        architecture=info.architecture or "ONNX", status="production",
        accuracy=metrics.get("test_accuracy") * 100 if metrics.get("test_accuracy") is not None else None,
        f1_macro=metrics.get("test_f1_score", metrics.get("test_f1")) if info.metric_averaging == "macro" else None,
        precision_macro=metrics.get("test_precision") if info.metric_averaging == "macro" else None,
        recall_macro=metrics.get("test_recall") if info.metric_averaging == "macro" else None,
        size_mb=None, weights_file_name="", weights_sha256=info.weights_sha256 or None,
        mlflow_model_name=info.model_name,
        mlflow_model_version=int(info.model_version) if info.model_version.isdecimal() else None,
        mlflow_run_id=info.run_id or None, mlflow_artifact_uri=info.model_uri,
        active_since=date.today(),
    )
    session.add(model)
    await session.flush()
    return model
