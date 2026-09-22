"""Esquemas del panel analítico."""

from __future__ import annotations

from app.schemas.common import EsquemaBase


class DashboardKpis(EsquemaBase):
    training_images: int
    training_images_breakdown: str
    model_accuracy: float
    model_accuracy_delta_pts: float
    user_predictions: int
    user_predictions_this_month: int
    active_countries: int
    active_continents: int


class DistribucionPorClase(EsquemaBase):
    glioma: int
    meningioma: int
    pituitary: int
    healthy: int


class CargasPorMes(EsquemaBase):
    month: str
    uploads: int


class PerfilCargasRecientes(EsquemaBase):
    axis: str
    value: float


class CargasPorPais(EsquemaBase):
    country_code: str
    country_name: str
    uploads: int


class MuestraDataset(EsquemaBase):
    tumor_class: str
    file_name: str


class Pais(EsquemaBase):
    code: str
    name: str
    latitude: float
    longitude: float
