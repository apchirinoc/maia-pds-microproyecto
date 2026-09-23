"""Paridad e integridad de un paquete movido fuera del entorno de entrenamiento."""
import shutil
import sys
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))
from app.ml.mlflow_engine import MlflowInferenceEngine
from pipelines.packaging import log_classifier


def test_package_can_move_and_preserves_scores(tmp_path, onnx_model_path, sample_image, preprocess_config, monkeypatch):
    original = tmp_path / "original"
    log_classifier(onnx_model_path, sample_image=sample_image, output_directory=original,
                   extra_metadata={"model_version": "portable-1"})
    expected = mlflow.pyfunc.load_model(str(original)).predict(pd.DataFrame({"image": [sample_image]}))
    moved = tmp_path / "relocated"
    shutil.move(original, moved)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:1")
    engine = MlflowInferenceEngine("fixture", model_uri=str(moved),
                                   expected_preprocess_fingerprint=preprocess_config.fingerprint)
    actual = engine.classify([sample_image])[0]
    np.testing.assert_allclose([s.confidence for s in actual.scores], expected.iloc[0].to_numpy())
    assert engine.describe().model_version == "portable-1"
    assert not engine.describe().simulated
    assert len(engine.describe().weights_sha256) == 64
    weights = next(moved.rglob("*.onnx"))
    weights.write_bytes(weights.read_bytes() + b"corrupt")
    with pytest.raises(Exception, match="(?i)(hash|huella|pesos|sha256)"):
        mlflow.pyfunc.load_model(str(moved))
