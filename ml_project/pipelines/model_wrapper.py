"""Envoltorio `pyfunc` que empaqueta preprocesamiento, inferencia y explicacion.

El artefacto resultante recibe **bytes de imagen** y devuelve probabilidades
por clase. El servicio que lo consume no conoce ni el tamano de entrada, ni
CLAHE, ni la normalizacion: todo viaja dentro del modelo.

Lo mismo vale para la explicabilidad (patron «Explainable Predictions»): el
mapa de influencia se calcula aqui dentro, sobre el tensor exacto que vio el
modelo, y se pide con el parametro `explain` del mecanismo `params` de MLflow.
Sin ese parametro la salida es la de siempre: el DataFrame de probabilidades.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import onnxruntime as ort
import pandas as pd

from pipelines.config import (
    CLASSIFIER_META_ARTIFACT,
    ONNX_MODEL_ARTIFACT,
    PREPROCESS_CONFIG_ARTIFACT,
)
from pipelines.explainability import (
    DEFAULT_OCCLUSION_CONFIG,
    OCCLUSION_METHOD_ID,
    OcclusionConfig,
    compute_occlusion_map,
    encode_influence_map,
)
from pipelines.preprocessing import MriPreprocessor, PreprocessConfig

IMAGE_COLUMN = "image"

EXPLAIN_PARAM = "explain"
"""Activa el calculo del mapa de influencia. Por defecto, desactivado."""

EXPLAIN_PATCH_SIZE_PARAM = "explain_patch_size"
EXPLAIN_STRIDE_PARAM = "explain_stride"

EXPLANATION_COLUMN = "explanation_png"
"""Mapa de influencia como PNG RGBA en base64 (la influencia va en el alfa)."""

EXPLANATION_METHOD_COLUMN = "explanation_method"
EXPLANATION_METHOD_LABEL_COLUMN = "explanation_method_label"


EXPLANATION_META_KEY = "explanation"
"""Clave de `classifier_meta` donde viaja la configuracion de la oclusion."""


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=1, keepdims=True)


def _read_occlusion_config(meta: dict[str, Any]) -> OcclusionConfig:
    """Recupera la configuracion de oclusion empaquetada con el modelo.

    Un artefacto anterior a esta funcionalidad no trae la clave; en ese caso se
    usa la configuracion por defecto y el modelo sigue cargando sin errores.
    """
    raw = meta.get(EXPLANATION_META_KEY)
    if not isinstance(raw, dict):
        return DEFAULT_OCCLUSION_CONFIG
    return OcclusionConfig(
        patch_size=int(raw.get("patch_size", DEFAULT_OCCLUSION_CONFIG.patch_size)),
        stride=int(raw.get("stride", DEFAULT_OCCLUSION_CONFIG.stride)),
        occlusion_value=float(
            raw.get("occlusion_value", DEFAULT_OCCLUSION_CONFIG.occlusion_value)
        ),
        batch_size=int(raw.get("batch_size", DEFAULT_OCCLUSION_CONFIG.batch_size)),
        max_passes=int(raw.get("max_passes", DEFAULT_OCCLUSION_CONFIG.max_passes)),
    )


class BrainTumorClassifier(mlflow.pyfunc.PythonModel):
    """Clasificador de tumores cerebrales listo para servir.

    Entrada: DataFrame con una columna `image` de bytes crudos (JPG o PNG).
    Salida: DataFrame con una columna por clase, con la probabilidad asociada.

    Con `params={"explain": True}` se anaden tres columnas mas: el mapa de
    influencia serializado y la identificacion del metodo que lo produjo.
    """

    def load_context(self, context: Any) -> None:
        config_path = Path(context.artifacts[PREPROCESS_CONFIG_ARTIFACT])
        self._config = PreprocessConfig.from_json(config_path.read_text(encoding="utf-8"))
        self._preprocessor = MriPreprocessor(self._config)

        meta_path = Path(context.artifacts[CLASSIFIER_META_ARTIFACT])
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self._classes: list[str] = list(meta["classes"])
        self._output_is_probability: bool = bool(meta["output_is_probability"])
        self._explanation_config = _read_occlusion_config(meta)

        self._session = ort.InferenceSession(
            context.artifacts[ONNX_MODEL_ARTIFACT], providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name

    @property
    def preprocess_fingerprint(self) -> str:
        """Huella del preprocesamiento realmente empaquetado."""
        return self._config.fingerprint

    @property
    def preprocess_label(self) -> str:
        """Etiqueta legible del preprocesamiento, para mostrar en la interfaz."""
        return self._config.label

    @property
    def explanation_label(self) -> str:
        """Etiqueta legible del metodo de explicabilidad empaquetado."""
        return self._explanation_config.label

    def _resolve_occlusion_config(self, params: dict[str, Any]) -> OcclusionConfig:
        """Aplica las sobrescrituras puntuales que permite la firma.

        El artefacto manda: si la peticion no indica nada, se usa la
        configuracion con la que se empaqueto el modelo.
        """
        patch_size = params.get(EXPLAIN_PATCH_SIZE_PARAM)
        stride = params.get(EXPLAIN_STRIDE_PARAM)
        if patch_size is None and stride is None:
            return self._explanation_config
        return OcclusionConfig(
            patch_size=int(patch_size) if patch_size is not None else self._explanation_config.patch_size,
            stride=int(stride) if stride is not None else self._explanation_config.stride,
            occlusion_value=self._explanation_config.occlusion_value,
            batch_size=self._explanation_config.batch_size,
            max_passes=self._explanation_config.max_passes,
        )

    def _explain(self, batch: np.ndarray, scores: np.ndarray, params: dict[str, Any]) -> dict[str, list[str]]:
        """Calcula un mapa de influencia por imagen del lote.

        Se explica la clase predicha de cada fila: es la afirmacion que el
        usuario ve y, por tanto, la que hay que justificar.
        """
        config = self._resolve_occlusion_config(params)
        mapas = []
        for index in range(batch.shape[0]):
            influencia = compute_occlusion_map(
                batch[index],
                self._session,
                int(np.argmax(scores[index])),
                config=config,
                output_is_probability=self._output_is_probability,
                input_name=self._input_name,
            )
            mapas.append(encode_influence_map(influencia))

        return {
            EXPLANATION_COLUMN: mapas,
            EXPLANATION_METHOD_COLUMN: [OCCLUSION_METHOD_ID] * len(mapas),
            EXPLANATION_METHOD_LABEL_COLUMN: [config.label] * len(mapas),
        }

    @staticmethod
    def _extract_images(model_input: Any) -> list[bytes]:
        if isinstance(model_input, pd.DataFrame):
            if IMAGE_COLUMN not in model_input.columns:
                raise KeyError(
                    f"Se esperaba una columna {IMAGE_COLUMN!r}; "
                    f"recibidas {list(model_input.columns)}"
                )
            values = model_input[IMAGE_COLUMN].tolist()
        elif isinstance(model_input, (list, tuple)):
            values = list(model_input)
        elif isinstance(model_input, (bytes, bytearray)):
            values = [model_input]
        else:
            raise TypeError(f"Entrada no soportada: {type(model_input)!r}")

        return [bytes(value) for value in values]

    def predict(self, context, model_input, params=None) -> pd.DataFrame:
        images = self._extract_images(model_input)
        batch = self._preprocessor.batch(images)
        outputs = self._session.run(None, {self._input_name: batch})[0]
        scores = np.asarray(outputs, dtype=np.float32)

        if not self._output_is_probability:
            scores = _softmax(scores)

        if scores.shape[1] != len(self._classes):
            raise ValueError(
                f"El modelo devolvio {scores.shape[1]} salidas y se esperaban "
                f"{len(self._classes)} clases"
            )

        frame = pd.DataFrame(scores.astype(np.float64), columns=self._classes)

        resolved_params = dict(params or {})
        if not bool(resolved_params.get(EXPLAIN_PARAM, False)):
            # Camino por defecto: exactamente la salida de siempre. La
            # explicacion cuesta N pasadas extra por imagen y solo se paga
            # cuando alguien la pide de forma explicita.
            return frame

        for column, values in self._explain(batch, scores, resolved_params).items():
            frame[column] = values
        return frame
