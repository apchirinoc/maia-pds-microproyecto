"""Registro de modelos.

Con `DATA_SOURCE=seed` estos datos vienen de memoria. Con MLflow activo
(§12 del plan) el mismo contrato lo sirve `MlflowRegistry`, sin tocar routers.
"""

from __future__ import annotations

from typing import Any, Final

RESUMEN_REGISTRO: Final[dict[str, Any]] = {
    "production_model": {"name": "EffNetB3-BT", "version": "v2.4"},
    "active_since": "2026-08-12",
    "accuracy_test": 98.4,
    "mean_latency_ms": 184,
    "storage_gb": 6.2,
    "archived_versions": 2,
}

MODELOS: Final[list[dict[str, Any]]] = [
    {
        "id": "effnetb3-bt-v2.4",
        "name": "EffNetB3-BT",
        "version": "v2.4",
        "architecture": "EfficientNet-B3",
        "accuracy": 98.4,
        "f1": 0.981,
        "size_mb": 47,
        "status": "production",
        "weights_file_name": "effnetb3_bt_v2.4.onnx",
    },
    {
        "id": "effnetb3-bt-v2.3",
        "name": "EffNetB3-BT",
        "version": "v2.3",
        "architecture": "EfficientNet-B3",
        "accuracy": 97.2,
        "f1": 0.968,
        "size_mb": 47.3,
        "status": "archived",
        "weights_file_name": "effnetb3_bt_v2.3.onnx",
    },
    {
        "id": "resnet50-bt-v1.8",
        "name": "ResNet50-BT",
        "version": "v1.8",
        "architecture": "ResNet-50",
        "accuracy": 95.6,
        "f1": 0.951,
        "size_mb": 98.4,
        "status": "archived",
        "weights_file_name": "resnet50_bt_v1.8.h5",
    },
    {
        "id": "vit-b16-bt-v0.9",
        "name": "ViT-B16-BT",
        "version": "v0.9",
        "architecture": "ViT-B/16",
        "accuracy": 96.9,
        "f1": 0.964,
        "size_mb": 331,
        "status": "validation",
        "weights_file_name": "vit_b16_v0.9.pt",
    },
    {
        "id": "cnn-base-v1.0",
        "name": "CNN-Base",
        "version": "v1.0",
        "architecture": "CNN · 6 capas",
        "accuracy": 91.3,
        "f1": 0.902,
        "size_mb": 12.8,
        "status": "baseline",
        "weights_file_name": "cnn_base_v1.0.h5",
    },
]


def _matriz_confusion(intensidad_diagonal: float) -> dict[str, dict[str, int]]:
    fuera = round((1 - intensidad_diagonal) * 12)
    return {
        "glioma": {"glioma": 295, "meningioma": 4, "pituitary": 1, "healthy": fuera},
        "meningioma": {"glioma": 6, "meningioma": 297, "pituitary": 3, "healthy": fuera},
        "pituitary": {"glioma": 1, "meningioma": 2, "pituitary": 297, "healthy": fuera},
        "healthy": {"glioma": 0, "meningioma": 1, "pituitary": 0, "healthy": 404},
    }


_HISTORIAL_POR_DEFECTO = [
    {"id": "evt-1", "label": "deployedToProduction", "date": "2026-04-12", "author": "m.rivera"},
    {"id": "evt-2", "label": "validated", "date": "2026-04-10", "author": "a.suarez"},
    {"id": "evt-3", "label": "trainingCompleted", "date": "2026-04-06", "author": "pipeline-ci"},
]

DETALLES_MODELO: Final[dict[str, dict[str, Any]]] = {
    "effnetb3-bt-v2.4": {
        **MODELOS[0],
        "training_images": 5712,
        "test_images": 1311,
        "active_since": "2026-08-12",
        "metrics": {
            "accuracy": 98.4,
            "precision_macro": 0.983,
            "recall_macro": 0.979,
            "auc": 0.997,
        },
        "confusion_matrix": _matriz_confusion(0.98),
        "class_performance": {
            "glioma": 0.983,
            "meningioma": 0.97,
            "pituitary": 0.99,
            "healthy": 0.997,
        },
        "deployment_history": _HISTORIAL_POR_DEFECTO,
        "target_draft_version": "v2.5",
        "previous_version": "v2.3",
    },
    "effnetb3-bt-v2.3": {
        **MODELOS[1],
        "training_images": 5400,
        "test_images": 1280,
        "active_since": "2026-02-02",
        "metrics": {
            "accuracy": 97.2,
            "precision_macro": 0.969,
            "recall_macro": 0.966,
            "auc": 0.992,
        },
        "confusion_matrix": _matriz_confusion(0.95),
        "class_performance": {
            "glioma": 0.965,
            "meningioma": 0.958,
            "pituitary": 0.972,
            "healthy": 0.988,
        },
        "deployment_history": [
            {"id": "evt-1", "label": "archived", "date": "2026-08-12", "author": "m.rivera"},
            {
                "id": "evt-2",
                "label": "deployedToProduction",
                "date": "2026-02-02",
                "author": "m.rivera",
            },
        ],
        "target_draft_version": "v2.4",
    },
    "resnet50-bt-v1.8": {
        **MODELOS[2],
        "training_images": 5100,
        "test_images": 1200,
        "active_since": "2025-10-18",
        "metrics": {
            "accuracy": 95.6,
            "precision_macro": 0.949,
            "recall_macro": 0.944,
            "auc": 0.981,
        },
        "confusion_matrix": _matriz_confusion(0.9),
        "class_performance": {
            "glioma": 0.941,
            "meningioma": 0.932,
            "pituitary": 0.951,
            "healthy": 0.97,
        },
        "deployment_history": [
            {"id": "evt-1", "label": "archived", "date": "2026-02-02", "author": "a.suarez"},
            {
                "id": "evt-2",
                "label": "deployedToProduction",
                "date": "2025-10-18",
                "author": "a.suarez",
            },
        ],
        "target_draft_version": "v1.9",
    },
    "vit-b16-bt-v0.9": {
        **MODELOS[3],
        "training_images": 5712,
        "test_images": 1311,
        "active_since": "",
        "metrics": {
            "accuracy": 96.9,
            "precision_macro": 0.962,
            "recall_macro": 0.958,
            "auc": 0.989,
        },
        "confusion_matrix": _matriz_confusion(0.93),
        "class_performance": {
            "glioma": 0.955,
            "meningioma": 0.948,
            "pituitary": 0.964,
            "healthy": 0.981,
        },
        "deployment_history": [
            {"id": "evt-1", "label": "validated", "date": "2026-08-28", "author": "a.suarez"},
            {
                "id": "evt-2",
                "label": "trainingCompleted",
                "date": "2026-08-20",
                "author": "pipeline-ci",
            },
        ],
        "target_draft_version": "v0.9",
    },
    "cnn-base-v1.0": {
        **MODELOS[4],
        "training_images": 4800,
        "test_images": 1100,
        "active_since": "2025-01-05",
        "metrics": {
            "accuracy": 91.3,
            "precision_macro": 0.905,
            "recall_macro": 0.898,
            "auc": 0.951,
        },
        "confusion_matrix": _matriz_confusion(0.8),
        "class_performance": {
            "glioma": 0.891,
            "meningioma": 0.879,
            "pituitary": 0.902,
            "healthy": 0.94,
        },
        "deployment_history": [
            {
                "id": "evt-1",
                "label": "trainingCompleted",
                "date": "2025-01-05",
                "author": "pipeline-ci",
            }
        ],
        "target_draft_version": "v1.1",
    },
}
