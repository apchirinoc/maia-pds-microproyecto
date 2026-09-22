"""Agregados del panel analítico."""

from __future__ import annotations

from typing import Final

KPIS_PANEL: Final[dict[str, object]] = {
    "training_images": 7023,
    "training_images_breakdown": "5 712 train · 1 311 test",
    "model_accuracy": 98.4,
    "model_accuracy_delta_pts": 1.2,
    "user_predictions": 12847,
    "user_predictions_this_month": 1380,
    "active_countries": 28,
    "active_continents": 4,
}

DISTRIBUCION_POR_CLASE: Final[dict[str, int]] = {
    "glioma": 1621,
    "meningioma": 1645,
    "pituitary": 1757,
    "healthy": 2000,
}

CARGAS_POR_MES: Final[list[dict[str, object]]] = [
    {"month": "S", "uploads": 520},
    {"month": "O", "uploads": 610},
    {"month": "N", "uploads": 690},
    {"month": "D", "uploads": 740},
    {"month": "E", "uploads": 820},
    {"month": "F", "uploads": 880},
    {"month": "M", "uploads": 940},
    {"month": "A", "uploads": 1010},
    {"month": "M", "uploads": 1080},
    {"month": "J", "uploads": 1150},
    {"month": "J", "uploads": 1220},
    {"month": "A", "uploads": 1300},
]

PERFIL_CARGAS_RECIENTES: Final[list[dict[str, object]]] = [
    {"axis": "glioma", "value": 78},
    {"axis": "meningioma", "value": 62},
    {"axis": "pituitary", "value": 55},
    {"axis": "healthy", "value": 90},
    {"axis": "confidence", "value": 94},
    {"axis": "volume", "value": 70},
]

MUESTRAS_DATASET: Final[list[dict[str, str]]] = [
    {"tumor_class": "glioma", "file_name": "Te-gl_0231.jpg"},
    {"tumor_class": "meningioma", "file_name": "Te-me_0118.jpg"},
    {"tumor_class": "pituitary", "file_name": "Te-pi_0204.jpg"},
    {"tumor_class": "healthy", "file_name": "Te-no_0092.jpg"},
]
