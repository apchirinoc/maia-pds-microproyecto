"""Esquemas del registro de modelos."""

from __future__ import annotations

from typing import Literal

from app.schemas.common import EsquemaBase

EstadoModelo = Literal["production", "archived", "validation", "baseline"]


class ModeloDesplegado(EsquemaBase):
    id: str
    name: str
    version: str
    architecture: str
    accuracy: float
    f1: float
    size_mb: float
    status: EstadoModelo
    weights_file_name: str


class MetricasModelo(EsquemaBase):
    accuracy: float
    precision_macro: float
    recall_macro: float
    auc: float


class EventoDespliegue(EsquemaBase):
    id: str
    label: str
    date: str
    author: str


class DetalleModelo(ModeloDesplegado):
    training_images: int
    test_images: int
    active_since: str
    metrics: MetricasModelo
    confusion_matrix: dict[str, dict[str, int]]
    class_performance: dict[str, float]
    deployment_history: list[EventoDespliegue]
    target_draft_version: str
    previous_version: str | None = None


class ModeloEnProduccion(EsquemaBase):
    name: str
    version: str


class ResumenRegistroModelos(EsquemaBase):
    production_model: ModeloEnProduccion
    active_since: str
    accuracy_test: float
    mean_latency_ms: int
    storage_gb: float
    archived_versions: int
