"""Prueba central del patron «Transform».

Demuestra que el preprocesamiento viaja dentro del artefacto y que el modelo
servido aplica exactamente el mismo que se uso al entrenar. Si alguien
reimplementa el preprocesamiento en el servicio, estas pruebas fallan.
"""

from __future__ import annotations

from pathlib import Path

import mlflow
import numpy as np
import onnxruntime as ort
import pandas as pd
import pytest

from pipelines.config import TUMOR_CLASSES
from pipelines.model_wrapper import IMAGE_COLUMN
from pipelines.packaging import log_classifier, predict_probabilities
from pipelines.preprocessing import MriPreprocessor, PreprocessConfig
from tests.conftest import encode_synthetic_mri


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=1, keepdims=True)


@pytest.fixture(scope="module")
def logged_model(tmp_path_factory, onnx_model_path, sample_image, preprocess_config):
    """Registra el clasificador contra un tracking store efimero.

    Se usa SQLite porque MLflow 3 retiro el backend de ficheros; en despliegue
    el backend es Postgres, segun la seccion 12.3 del plan.
    """
    workspace = tmp_path_factory.mktemp("mlflow")
    mlflow.set_tracking_uri(f"sqlite:///{workspace / 'mlflow.db'}")
    artifacts = workspace / "artifacts"
    artifacts.mkdir()
    experiment_id = mlflow.create_experiment(
        "transform-parity", artifact_location=artifacts.as_uri()
    )
    mlflow.set_experiment(experiment_id=experiment_id)

    with mlflow.start_run():
        info = log_classifier(
            onnx_model_path,
            sample_image=sample_image,
            preprocess_config=preprocess_config,
            output_is_probability=False,
        )
    return info


def test_el_codigo_de_preprocesamiento_viaja_dentro_del_artefacto(logged_model):
    """El fallo que previene el patron: pesos sin el codigo que los alimenta."""
    local_path = Path(mlflow.artifacts.download_artifacts(logged_model.model_uri))
    empaquetado = local_path / "code" / "pipelines" / "preprocessing.py"
    assert empaquetado.is_file(), (
        "preprocessing.py no viaja con el modelo: el servicio tendria que "
        "reimplementarlo y quedaria expuesto a desviacion entrenamiento-servicio"
    )
    assert (local_path / "code" / "pipelines" / "model_wrapper.py").is_file()


def test_la_configuracion_del_preprocesamiento_queda_en_los_metadatos(
    logged_model, preprocess_config
):
    metadata = mlflow.models.Model.load(logged_model.model_uri).metadata
    assert metadata["preprocess_fingerprint"] == preprocess_config.fingerprint
    assert metadata["preprocess_label"] == preprocess_config.label
    assert metadata["classes"] == list(TUMOR_CLASSES)


def test_entrenamiento_y_servicio_aplican_el_mismo_preprocesamiento(
    logged_model, onnx_model_path, preprocess_config
):
    """Paridad de extremo a extremo sobre varias imagenes distintas.

    Camino A (entrenamiento): preprocesador local mas sesion ONNX directa.
    Camino B (servicio): el modelo cargado desde MLflow.
    El modelo ONNX de prueba es sensible a cada pixel, asi que la igualdad de
    salidas implica que el tensor de entrada fue identico.
    """
    imagenes = [encode_synthetic_mri(seed=seed) for seed in (11, 22, 33)]

    procesador = MriPreprocessor(preprocess_config)
    sesion = ort.InferenceSession(str(onnx_model_path), providers=["CPUExecutionProvider"])
    nombre_entrada = sesion.get_inputs()[0].name
    esperado = _softmax(sesion.run(None, {nombre_entrada: procesador.batch(imagenes)})[0])

    servido = mlflow.pyfunc.load_model(logged_model.model_uri)
    obtenido = predict_probabilities(servido, imagenes)

    np.testing.assert_allclose(obtenido, esperado, rtol=1e-6, atol=1e-7)


def test_la_prueba_de_paridad_detecta_una_desviacion_real(
    logged_model, onnx_model_path, sample_image
):
    """Control negativo: si el servicio usara otro preprocesamiento, se nota.

    Sin esta prueba, la anterior podria pasar por casualidad aunque el modelo
    fuese insensible a la entrada.
    """
    desviado = MriPreprocessor(PreprocessConfig(clahe_clip_limit=8.0, interpolation="area"))
    sesion = ort.InferenceSession(str(onnx_model_path), providers=["CPUExecutionProvider"])
    nombre_entrada = sesion.get_inputs()[0].name
    con_desviacion = _softmax(
        sesion.run(None, {nombre_entrada: desviado.batch([sample_image])})[0]
    )

    servido = mlflow.pyfunc.load_model(logged_model.model_uri)
    correcto = predict_probabilities(servido, [sample_image])

    assert not np.allclose(correcto, con_desviacion, rtol=1e-3), (
        "El modelo de prueba no distingue preprocesamientos distintos; "
        "la prueba de paridad no probaria nada"
    )


def test_la_salida_respeta_la_firma_declarada(logged_model, sample_image):
    servido = mlflow.pyfunc.load_model(logged_model.model_uri)
    resultado = servido.predict(pd.DataFrame({IMAGE_COLUMN: [sample_image]}))

    assert list(resultado.columns) == list(TUMOR_CLASSES)
    assert resultado.shape == (1, len(TUMOR_CLASSES))
    np.testing.assert_allclose(resultado.to_numpy().sum(axis=1), 1.0, rtol=1e-6)
    assert (resultado.to_numpy() >= 0).all()


def test_acepta_lotes_de_varias_imagenes(logged_model):
    imagenes = [encode_synthetic_mri(seed=seed) for seed in range(5)]
    servido = mlflow.pyfunc.load_model(logged_model.model_uri)
    resultado = predict_probabilities(servido, imagenes)
    assert resultado.shape == (5, len(TUMOR_CLASSES))


def test_el_servicio_detecta_una_configuracion_divergente(logged_model):
    """Defensa en profundidad: la huella permite abortar antes de servir."""
    metadata = mlflow.models.Model.load(logged_model.model_uri).metadata
    huella_del_artefacto = metadata["preprocess_fingerprint"]

    assert huella_del_artefacto == PreprocessConfig().fingerprint
    assert huella_del_artefacto != PreprocessConfig(target_size=256).fingerprint
