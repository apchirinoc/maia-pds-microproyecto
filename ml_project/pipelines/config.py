"""Constantes compartidas del proyecto de ML."""

from __future__ import annotations

from typing import Final

TUMOR_CLASSES: Final[tuple[str, ...]] = ("glioma", "meningioma", "pituitary", "healthy")
"""Orden canonico de las clases.

Coincide literalmente con el tipo `TumorClass` del frontend y con el catalogo
`tumor_classes` de Postgres: los mismos literales en las tres capas, sin
traducciones intermedias.
"""

REGISTERED_MODEL_NAME: Final[str] = "brain-tumor-classifier"
CHAMPION_ALIAS: Final[str] = "champion"
CHALLENGER_ALIAS: Final[str] = "challenger"

PREPROCESS_CONFIG_ARTIFACT: Final[str] = "preprocess_config"
CLASSIFIER_META_ARTIFACT: Final[str] = "classifier_meta"
ONNX_MODEL_ARTIFACT: Final[str] = "onnx_model"
