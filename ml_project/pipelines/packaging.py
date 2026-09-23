"""Empaquetado del clasificador como modelo `pyfunc` de MLflow.

Registra en un unico artefacto: los pesos ONNX, la configuracion del
preprocesamiento, el codigo que lo implementa (`code_paths`) y la firma de
entrada/salida. Cualquier consumidor obtiene el modelo completo, no solo los
pesos.
"""

from __future__ import annotations

import json
import hashlib
from importlib.metadata import version
import tempfile
from pathlib import Path
from typing import Any, Sequence

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import ModelSignature
from mlflow.types import ColSpec, DataType, ParamSchema, ParamSpec, Schema

from pipelines.config import (
    CLASSIFIER_META_ARTIFACT,
    ONNX_MODEL_ARTIFACT,
    PREPROCESS_CONFIG_ARTIFACT,
    TUMOR_CLASSES,
)
from pipelines.explainability import (
    DEFAULT_OCCLUSION_CONFIG,
    OCCLUSION_METHOD_ID,
    OcclusionConfig,
)
from pipelines.model_wrapper import (
    EXPLAIN_PARAM,
    EXPLAIN_PATCH_SIZE_PARAM,
    EXPLAIN_STRIDE_PARAM,
    EXPLANATION_COLUMN,
    EXPLANATION_META_KEY,
    IMAGE_COLUMN,
    BrainTumorClassifier,
)
from pipelines.preprocessing import PreprocessConfig

PACKAGE_DIR = Path(__file__).resolve().parent


def build_signature(
    classes: Sequence[str],
    *,
    explanation_config: OcclusionConfig = DEFAULT_OCCLUSION_CONFIG,
) -> ModelSignature:
    """Firma del modelo: bytes de imagen a probabilidades por clase.

    Los `params` declaran la explicabilidad como una capacidad opcional del
    artefacto. `explain` vale `False` por defecto, de modo que ningun
    consumidor existente cambia de comportamiento ni paga el coste extra; el
    que quiera la explicacion tiene que pedirla. Los otros dos parametros
    permiten negociar resolucion frente a coste sin reempaquetar el modelo.
    """
    inputs = Schema([ColSpec(DataType.binary, IMAGE_COLUMN)])
    outputs = Schema([ColSpec(DataType.double, name) for name in classes])
    params = ParamSchema(
        [
            ParamSpec(EXPLAIN_PARAM, DataType.boolean, False),
            ParamSpec(EXPLAIN_PATCH_SIZE_PARAM, DataType.long, explanation_config.patch_size),
            ParamSpec(EXPLAIN_STRIDE_PARAM, DataType.long, explanation_config.stride),
        ]
    )
    return ModelSignature(inputs=inputs, outputs=outputs, params=params)


def build_input_example(sample_image: bytes) -> pd.DataFrame:
    return pd.DataFrame({IMAGE_COLUMN: [sample_image]})


def log_classifier(
    onnx_model_path: str | Path,
    *,
    sample_image: bytes,
    preprocess_config: PreprocessConfig | None = None,
    classes: Sequence[str] = TUMOR_CLASSES,
    output_is_probability: bool = False,
    explanation_config: OcclusionConfig | None = None,
    name: str = "model",
    registered_model_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
    output_directory: str | Path | None = None,
) -> Any:
    """Registra el clasificador completo en el run activo de MLflow.

    `sample_image` se usa como ejemplo de entrada: MLflow lo almacena y lo
    emplea para validar la firma al cargar el modelo.

    `explanation_config` viaja en los metadatos para que el servicio pueda
    declarar que metodo de explicabilidad esta sirviendo sin tener que
    conocerlo ni reimplementarlo.
    """
    onnx_model_path = Path(onnx_model_path).resolve()
    if not onnx_model_path.is_file():
        raise FileNotFoundError(f"No existe el modelo ONNX en {onnx_model_path}")

    config = preprocess_config or PreprocessConfig()
    explanation = explanation_config or DEFAULT_OCCLUSION_CONFIG
    metadata = {
        **(extra_metadata or {}),
        "classes": list(classes),
        "weights_sha256": hashlib.sha256(onnx_model_path.read_bytes()).hexdigest(),
        "output_is_probability": output_is_probability,
        "preprocess_fingerprint": config.fingerprint,
        "preprocess_label": config.label,
        "explanation_method": OCCLUSION_METHOD_ID,
        "explanation_label": explanation.label,
        EXPLANATION_META_KEY: explanation.to_dict(),
    }

    with tempfile.TemporaryDirectory() as staging:
        staging_dir = Path(staging)
        config_file = staging_dir / "preprocess_config.json"
        config_file.write_text(config.to_json(), encoding="utf-8")
        meta_file = staging_dir / "classifier_meta.json"
        meta_file.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")

        kwargs = dict(
            python_model=BrainTumorClassifier(),
            artifacts={
                ONNX_MODEL_ARTIFACT: str(onnx_model_path),
                PREPROCESS_CONFIG_ARTIFACT: str(config_file),
                CLASSIFIER_META_ARTIFACT: str(meta_file),
            },
            code_paths=[str(PACKAGE_DIR)],
            signature=build_signature(classes, explanation_config=explanation),
            input_example=build_input_example(sample_image),
            metadata=metadata,
            pip_requirements=[
                f"{package}=={version(package)}" for package in
                ("mlflow", "cloudpickle", "numpy", "pandas", "onnxruntime", "opencv-python-headless", "Pillow")
            ],
        )
        if output_directory is not None:
            # Paquete portable: no crea runs ni requiere un servidor encendido.
            mlflow.pyfunc.save_model(path=str(output_directory), **kwargs)
            return Path(output_directory)

        mlflow.log_params(
            {
                "preprocess_target_size": config.target_size,
                "preprocess_clahe_clip_limit": config.clahe_clip_limit,
                "preprocess_interpolation": config.interpolation,
                "preprocess_fingerprint": config.fingerprint,
                "explanation_method": OCCLUSION_METHOD_ID,
                "explanation_patch_size": explanation.patch_size,
                "explanation_stride": explanation.stride,
            }
        )

        return mlflow.pyfunc.log_model(
            name=name,
            registered_model_name=registered_model_name,
            **kwargs,
        )


def predict_probabilities(model: Any, images: Sequence[bytes]) -> np.ndarray:
    """Utilidad para consumir un modelo cargado con `mlflow.pyfunc.load_model`."""
    frame = pd.DataFrame({IMAGE_COLUMN: list(images)})
    return model.predict(frame).to_numpy()


def predict_with_explanation(model: Any, images: Sequence[bytes]) -> pd.DataFrame:
    """Pide probabilidades **y** mapa de influencia en una sola llamada.

    Devuelve el DataFrame completo: una columna por clase mas la columna
    `explanation_png` con el mapa serializado y la identificacion del metodo.
    """
    frame = pd.DataFrame({IMAGE_COLUMN: list(images)})
    result = model.predict(frame, params={EXPLAIN_PARAM: True})
    if EXPLANATION_COLUMN not in result.columns:
        raise RuntimeError(
            "El artefacto no devolvio explicacion: comprueba que se empaqueto "
            "con una firma que declare el parametro 'explain'"
        )
    return result
