"""El adaptador HTTP no puede interpretar salidas incompatibles como predicciones."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))
from app.ml.mlflow_engine import MlflowInferenceEngine
from app.ml.engine import ModelContractError

CLASSES = ["glioma", "meningioma", "pituitary", "healthy"]


def engine(monkeypatch, frame, classes=CLASSES):
    metadata = SimpleNamespace(
        metadata={"classes": classes, "preprocess_label": "fixture", "preprocess_fingerprint": "fixture", "model_version": "fixture-v1"},
        run_id="run-fixture", signature=None,
    )
    fake = SimpleNamespace(metadata=metadata, predict=lambda inputs, **kwargs: frame)
    monkeypatch.setattr("mlflow.pyfunc.load_model", lambda uri: fake)
    return MlflowInferenceEngine("fixture", model_uri="runs:/fixture/model")


def test_preserves_scores_and_identity(monkeypatch):
    model = engine(monkeypatch, pd.DataFrame([[.1, .2, .6, .1]], columns=CLASSES))
    result = model.classify([b"fixture"])[0]
    assert result.predicted_class == "pituitary"
    assert result.confidence == .6
    assert model.describe().run_id == "run-fixture"
    assert model.describe().model_version == "fixture-v1"


@pytest.mark.parametrize("values", [[float("nan"), .2, .6, .2], [-.1, .2, .6, .3], [.1, .2, .3, .1]])
def test_invalid_probabilities_are_rejected(monkeypatch, values):
    model = engine(monkeypatch, pd.DataFrame([values], columns=CLASSES))
    with pytest.raises(ModelContractError):
        model.classify([b"fixture"])


def test_reordered_columns_are_rejected(monkeypatch):
    model = engine(monkeypatch, pd.DataFrame([[.1, .2, .6, .1]], columns=list(reversed(CLASSES))))
    with pytest.raises(ModelContractError):
        model.classify([b"fixture"])


def test_wrong_batch_size_is_rejected(monkeypatch):
    model = engine(monkeypatch, pd.DataFrame([[.1, .2, .6, .1]], columns=CLASSES))
    with pytest.raises(ModelContractError):
        model.classify([b"first", b"second"])
