"""Motor de inferencia respaldado por el Model Registry de MLflow.

Este modulo **no contiene preprocesamiento**: carga el modelo por alias y le
entrega los bytes de la imagen tal cual. Redimensionado, CLAHE y normalizacion
viven dentro del artefacto (patron «Transform»).

Tampoco contiene el metodo de explicabilidad. Para explicar una prediccion
enciende el parametro `explain` de la firma del modelo y transporta el mapa
que este devuelve. Si manana el artefacto cambia de oclusion a otro metodo,
este fichero no se toca: solo cambiara la etiqueta que el propio modelo
declara.
"""

from __future__ import annotations

import logging
import hashlib
import math
from pathlib import Path
from typing import Sequence

import mlflow
import pandas as pd

from app.ml.engine import (
    ClassScore,
    ExplanationNotSupportedError,
    InferenceEngine,
    InferenceResult,
    ModelInfo,
    ModelContractError,
    PredictionExplanation,
)

logger = logging.getLogger(__name__)

IMAGE_COLUMN = "image"

# Nombres del contrato que publica el artefacto. Son referencias, no
# implementacion: el servicio los usa para pedir y leer, nunca para calcular.
EXPLAIN_PARAM = "explain"
EXPLANATION_COLUMN = "explanation_png"
EXPLANATION_METHOD_COLUMN = "explanation_method"
EXPLANATION_METHOD_LABEL_COLUMN = "explanation_method_label"

_EXPLANATION_COLUMNS = frozenset(
    {EXPLANATION_COLUMN, EXPLANATION_METHOD_COLUMN, EXPLANATION_METHOD_LABEL_COLUMN}
)


class PreprocessMismatchError(RuntimeError):
    """El artefacto no declara el preprocesamiento esperado."""


class MlflowInferenceEngine(InferenceEngine):
    """Carga `models:/<nombre>@<alias>` y sirve predicciones.

    Args:
        model_name: nombre registrado en el Model Registry.
        alias: alias que determina que version sirve trafico (`champion`).
        expected_preprocess_fingerprint: si se indica, el motor rechaza arrancar
            cuando el artefacto declara otro preprocesamiento. Es defensa en
            profundidad frente a un despliegue mal empaquetado.
    """

    def __init__(
        self,
        model_name: str,
        *,
        alias: str = "champion",
        version: str | None = None,
        model_uri: str | None = None,
        tracking_uri: str | None = None,
        expected_preprocess_fingerprint: str | None = None,
    ) -> None:
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        resolved_version = version
        source_run_id = ""
        if not model_uri:
            client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
            registered = (
                client.get_model_version(model_name, version)
                if version else client.get_model_version_by_alias(model_name, alias)
            )
            resolved_version = str(registered.version)
            source_run_id = registered.run_id or ""
            model_uri = f"models:/{model_name}/{resolved_version}"
        self._model_uri = model_uri
        self._model = mlflow.pyfunc.load_model(self._model_uri)
        metadata = dict(self._model.metadata.metadata or {})

        classes = tuple(metadata.get("classes", ()))
        if len(classes) != 4 or set(classes) != {"glioma", "meningioma", "pituitary", "healthy"}:
            raise ModelContractError("El artefacto debe declarar las cuatro clases, en el orden de sus salidas")
        if not metadata.get("preprocess_label") or not metadata.get("preprocess_fingerprint"):
            raise ModelContractError("El artefacto debe declarar su preprocesamiento")
        weights_sha256 = str(metadata.get("weights_sha256", ""))
        run_id = source_run_id or self._model.metadata.run_id or str(metadata.get("source_run_id", ""))
        resolved_version = resolved_version or str(metadata.get("model_version", ""))
        if not resolved_version:
            resolved_version = "local-" + hashlib.sha256(
                Path(self._model_uri, "MLmodel").read_bytes()
                if Path(self._model_uri).is_dir() else self._model_uri.encode()
            ).hexdigest()[:12]

        fingerprint = str(metadata.get("preprocess_fingerprint", ""))
        if expected_preprocess_fingerprint and fingerprint != expected_preprocess_fingerprint:
            raise PreprocessMismatchError(
                f"El modelo {self._model_uri} declara el preprocesamiento "
                f"{fingerprint!r} y se esperaba {expected_preprocess_fingerprint!r}"
            )

        self._info = ModelInfo(
            model_version=resolved_version,
            model_name=model_name,
            model_uri=self._model_uri,
            run_id=run_id,
            weights_sha256=weights_sha256,
            architecture=str(metadata.get("architecture", metadata.get("arch", "ONNX"))),
            metric_averaging=str(metadata.get("metric_averaging", "unknown")),
            evaluation_metrics={
                key: float(value) for key, value in metadata.get("evaluation_metrics", {}).items()
                if isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1
            },
            preprocess_label=str(metadata.get("preprocess_label", "")),
            preprocess_fingerprint=fingerprint,
            classes=classes,
            simulated=False,
            explanation_method=str(metadata.get("explanation_method", "")),
            explanation_label=str(metadata.get("explanation_label", "")),
            supports_explanation=self._declares_explain_param(),
        )
        logger.info(
            "Modelo cargado desde %s (preprocesamiento %s, explicabilidad %s)",
            self._model_uri,
            self._info.preprocess_label,
            self._info.explanation_label or "no disponible",
        )

    def _declares_explain_param(self) -> bool:
        """Lee de la firma si el artefacto sabe explicarse.

        Es el propio modelo quien declara la capacidad. El servicio no la
        supone ni la suple: un artefacto antiguo simplemente no la ofrece.
        """
        signature = self._model.metadata.signature
        if signature is None or signature.params is None:
            return False
        return any(spec.name == EXPLAIN_PARAM for spec in signature.params.params)

    def describe(self) -> ModelInfo:
        return self._info

    def classify(self, images: Sequence[bytes], *, explain: bool = False) -> list[InferenceResult]:
        if not images:
            return []
        if explain and not self._info.supports_explanation:
            raise ExplanationNotSupportedError(
                f"El modelo {self._model_uri} no declara el parametro "
                f"{EXPLAIN_PARAM!r}: fue empaquetado sin capacidad de explicarse"
            )

        # Los bytes viajan sin transformar y la explicacion se pide, no se
        # calcula: el artefacto se encarga de ambas cosas.
        frame = pd.DataFrame({IMAGE_COLUMN: list(images)})
        predictions = (
            self._model.predict(frame, params={EXPLAIN_PARAM: True})
            if explain
            else self._model.predict(frame)
        )

        if not isinstance(predictions, pd.DataFrame):
            raise ModelContractError("El modelo debe devolver un DataFrame con las probabilidades por clase")
        class_columns = [
            column for column in predictions.columns if column not in _EXPLANATION_COLUMNS
        ]
        if tuple(class_columns) != self._info.classes or len(predictions) != len(images):
            raise ModelContractError("Las filas o clases devueltas no coinciden con el contrato del artefacto")

        results: list[InferenceResult] = []
        for _, row in predictions.iterrows():
            scores = tuple(
                ClassScore(tumor_class=str(name), confidence=float(row[name]))
                for name in class_columns
            )
            if any(not math.isfinite(score.confidence) or not 0 <= score.confidence <= 1 for score in scores):
                raise ModelContractError("El modelo devolvió probabilidades inválidas")
            if not math.isclose(sum(score.confidence for score in scores), 1.0, abs_tol=1e-4):
                raise ModelContractError("Las probabilidades del modelo no suman uno")
            best = max(scores, key=lambda score: score.confidence)
            results.append(
                InferenceResult(
                    predicted_class=best.tumor_class,
                    scores=scores,
                    model_version=self._info.model_version,
                    preprocess_label=self._info.preprocess_label,
                    explanation=self._read_explanation(row),
                )
            )
        return results

    def _read_explanation(self, row: pd.Series) -> PredictionExplanation | None:
        """Transporta el mapa que devolvio el artefacto, sin interpretarlo."""
        if EXPLANATION_COLUMN not in row.index:
            return None
        return PredictionExplanation(
            method=str(row.get(EXPLANATION_METHOD_COLUMN, self._info.explanation_method)),
            method_label=str(row.get(EXPLANATION_METHOD_LABEL_COLUMN, self._info.explanation_label)),
            influence_map_png=str(row[EXPLANATION_COLUMN]),
        )
