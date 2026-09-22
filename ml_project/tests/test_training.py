"""Pruebas del pipeline de entrenamiento.

Rapidas y en CPU: entrenan `SimpleCNN` una epoca sobre un dataset sintetico y
verifican (1) que las metricas salen en rango, (2) que el ONNX exportado tiene
la firma que espera el servicio y (3) que el artefacto empaquetado con
`log_classifier` se sirve y devuelve probabilidades. Un ultimo test corre la CLI
completa contra un MLflow efimero (SQLite) y comprueba el alias `champion`.

Se omiten si torch no esta instalado.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")  # noqa: F841  (guard: sin torch no hay entrenamiento)

import mlflow  # noqa: E402
import onnxruntime as ort  # noqa: E402

from pipelines.config import CHAMPION_ALIAS, REGISTERED_MODEL_NAME, TUMOR_CLASSES  # noqa: E402
from pipelines.dataset import particionar  # noqa: E402
from pipelines.dataset_io import escanear_directorio  # noqa: E402
from pipelines.packaging import log_classifier, predict_probabilities  # noqa: E402
from pipelines.preprocessing import MriPreprocessor, PreprocessConfig  # noqa: E402
from pipelines.training import TrainConfig, entrenar, evaluar, exportar_onnx  # noqa: E402
from tests.conftest import encode_synthetic_mri  # noqa: E402


def _dataset_sintetico(raiz: Path, por_clase: int = 4) -> None:
    for indice, carpeta in enumerate(("glioma", "meningioma", "pituitary", "notumor")):
        destino = raiz / carpeta
        destino.mkdir(parents=True)
        for j in range(por_clase):
            (destino / f"{carpeta}_{j}.png").write_bytes(
                encode_synthetic_mri(seed=indice * 100 + j)
            )


@pytest.fixture()
def datos(tmp_path):
    raiz = tmp_path / "data"
    _dataset_sintetico(raiz)
    registros, indice = escanear_directorio(raiz)
    return particionar(registros), indice


def _config() -> TrainConfig:
    return TrainConfig(arch="cnn_simple", epochs=1, batch_size=4, val_fraction=0.0)


def test_entrenar_y_evaluar_devuelve_metricas_en_rango(datos):
    particion, indice = datos
    model, historial = entrenar(_config(), particion.train, indice)

    assert len(historial) == 1
    metricas = evaluar(model, particion.train, indice)
    for clave in ("accuracy", "precision", "recall", "f1"):
        assert 0.0 <= metricas[clave] <= 1.0


def test_exportar_onnx_tiene_la_firma_esperada(datos, tmp_path):
    particion, indice = datos
    model, _ = entrenar(_config(), particion.train, indice)

    onnx_path = exportar_onnx(model, tmp_path / "modelo.onnx")
    sesion = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    entrada = sesion.get_inputs()[0]
    salida = sesion.get_outputs()[0]

    lado = PreprocessConfig().target_size
    assert list(entrada.shape[1:]) == [3, lado, lado]
    assert salida.shape[-1] == len(TUMOR_CLASSES)

    lote = MriPreprocessor().batch([encode_synthetic_mri(seed=1)])
    resultado = sesion.run(None, {entrada.name: lote})[0]
    assert resultado.shape == (1, len(TUMOR_CLASSES))


def test_round_trip_empaquetado_sirve_probabilidades(datos, tmp_path):
    particion, indice = datos
    model, _ = entrenar(_config(), particion.train, indice)
    onnx_path = exportar_onnx(model, tmp_path / "modelo.onnx")

    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    experimento = mlflow.create_experiment("train-roundtrip", artifact_location=artifacts.as_uri())
    mlflow.set_experiment(experiment_id=experimento)

    muestra = encode_synthetic_mri(seed=5)
    with mlflow.start_run():
        info = log_classifier(
            onnx_path,
            sample_image=muestra,
            preprocess_config=PreprocessConfig(),
            output_is_probability=False,
        )

    servido = mlflow.pyfunc.load_model(info.model_uri)
    probabilidades = predict_probabilities(servido, [muestra])

    assert probabilidades.shape == (1, len(TUMOR_CLASSES))
    np.testing.assert_allclose(probabilidades.sum(axis=1), 1.0, rtol=1e-6)


def test_cli_entrena_registra_y_fija_champion(tmp_path):
    from mlflow.tracking import MlflowClient

    from pipelines import train as train_cli

    raiz = tmp_path / "data"
    _dataset_sintetico(raiz, por_clase=5)
    tracking = f"sqlite:///{tmp_path / 'mlflow.db'}"
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    mlflow.set_tracking_uri(tracking)
    mlflow.create_experiment("cli-test", artifact_location=artifacts.as_uri())

    resultados = train_cli.main(
        [
            "--data-dir", str(raiz),
            "--arch", "cnn_simple",
            "--epochs", "1",
            "--batch-size", "4",
            "--tracking-uri", tracking,
            "--experiment", "cli-test",
        ]
    )

    assert len(resultados) == 1
    assert resultados[0]["version"] is not None

    cliente = MlflowClient(tracking_uri=tracking)
    campeon = cliente.get_model_version_by_alias(REGISTERED_MODEL_NAME, CHAMPION_ALIAS)
    assert campeon.version == resultados[0]["version"]
