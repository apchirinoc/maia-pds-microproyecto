"""Esquemas del histórico de cargas y de la verdad de campo."""

from __future__ import annotations

from typing import Literal

from app.schemas.common import EsquemaBase

ClaseTumor = Literal["glioma", "meningioma", "pituitary", "healthy"]
EstadoCarga = Literal["validated", "pending", "discarded"]
FuenteVerdadCampo = Literal[
    "specialist_review", "radiology_report", "follow_up_imaging", "histopathology"
]


class DiagnosticoConfirmado(EsquemaBase):
    diagnosis: ClaseTumor
    confirmed_by: str
    confirmed_at: str
    source: FuenteVerdadCampo


class RegistroCarga(EsquemaBase):
    id: str
    file_name: str
    captured_at: str
    country_name: str
    prediction: ClaseTumor
    confidence: float
    status: EstadoCarga
    ground_truth: DiagnosticoConfirmado | None = None


class MetricasVerdadCampo(EsquemaBase):
    total_uploads: int
    confirmed_uploads: int
    correct_predictions: int
    mismatched_predictions: int
    coverage: float
    measured_accuracy: float | None = None


class ResumenHistorico(EsquemaBase):
    total_uploads: int
    pending_review: int
    average_confidence: float
    discarded: int
    ground_truth: MetricasVerdadCampo


class RegistrarVerdadCampoEntrada(EsquemaBase):
    diagnosis: ClaseTumor
    confirmed_by: str
    source: FuenteVerdadCampo
