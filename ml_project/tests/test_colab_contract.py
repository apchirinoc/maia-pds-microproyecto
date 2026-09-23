"""Paridad con las transformaciones publicadas en el PR #28, sin reentrenar."""
import io
import json
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
from torchvision import transforms
from torchvision.models import resnet18
import mlflow.pytorch
import export_colab_model
from pipelines.preprocessing import MriPreprocessor, PreprocessConfig
from export_colab_model import export_package, COLAB_CLASSES


@pytest.mark.parametrize("mode,format", [("RGB", "JPEG"), ("RGB", "PNG"), ("L", "PNG"), ("RGBA", "PNG")])
def test_rgb_matches_notebook(mode, format):
    rgb = np.random.default_rng(42).integers(0, 256, (317, 289, 3), dtype=np.uint8)
    image = Image.fromarray(rgb).convert(mode)
    stream = io.BytesIO()
    image.save(stream, format=format)
    config = PreprocessConfig(mode="rgb_imagenet")
    notebook = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(),
                                   transforms.Normalize(config.mean, config.std)])
    with Image.open(io.BytesIO(stream.getvalue())) as decoded:
        expected = notebook(decoded.convert("RGB")).numpy()
    np.testing.assert_array_equal(MriPreprocessor(config).from_bytes(stream.getvalue()), expected)
    assert PreprocessConfig.from_json(config.to_json()) == config
    assert config.fingerprint != PreprocessConfig().fingerprint


def test_export_keeps_probabilities_and_class_order(tmp_path, sample_image):
    # Modelo pequeño con pesos arbitrarios: verifica conversión, no exactitud clínica.
    torch.manual_seed(42)
    model = torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten(), torch.nn.Linear(3, 4))
    result = export_package(model, [sample_image], tmp_path / "classifier", version="test-colab",
                            run_id="0" * 32)
    assert result["classes"] == list(COLAB_CLASSES)
    assert result["max_probability_difference"] < 1e-5


def test_resnet18_pytorch_package_exports_offline(tmp_path, sample_image, monkeypatch):
    # Arquitectura definitiva, pesos aleatorios: no representa el modelo entrenado.
    torch.manual_seed(42)
    model = resnet18(weights=None, num_classes=4).eval()
    mlflow.pytorch.save_model(model, str(tmp_path / "pytorch"),
                              serialization_format="pickle", pip_requirements=[])
    (tmp_path / "sample.png").write_bytes(sample_image)
    (tmp_path / "metrics.json").write_text(json.dumps({"test_accuracy": 0.5}))
    output = tmp_path / "classifier"
    monkeypatch.setattr(sys, "argv", ["export_colab_model.py", "--model-uri", str(tmp_path / "pytorch"),
                                     "--run-id", "0" * 32, "--version", "test-resnet18",
                                     "--architecture", "ResNet18", "--metrics", str(tmp_path / "metrics.json"),
                                     "--sample", str(tmp_path / "sample.png"), "--output", str(output)])
    export_colab_model.main()
    result = json.loads((output / "validation.json").read_text())
    saved = mlflow.pyfunc.load_model(str(output))
    assert saved.metadata.metadata["architecture"] == "ResNet18"
    assert saved.metadata.metadata["evaluation_metrics"] == {"test_accuracy": 0.5}
    assert saved.metadata.metadata["metric_averaging"] == "weighted"
    assert result["model_version"] == "test-resnet18"
    assert result["source_run_id"] == "0" * 32
    assert result["sample_count"] == 1
    assert len(result["weights_sha256"]) == 64
    # La carpeta temporal ya desapareció: la carga demuestra que el paquete se movió completo.
    assert list(saved.predict(pd.DataFrame({"image": [sample_image]})).columns) == list(COLAB_CLASSES)


def test_failed_parity_does_not_leave_a_package(tmp_path, sample_image, monkeypatch):
    model = torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten(), torch.nn.Linear(3, 4))
    broken = SimpleNamespace(predict=lambda frame: pd.DataFrame([[1.0, 0.0, 0.0, 0.0]], columns=COLAB_CLASSES))
    monkeypatch.setattr(export_colab_model.mlflow.pyfunc, "load_model", lambda path: broken)
    output = tmp_path / "classifier"
    with pytest.raises(AssertionError):
        export_package(model, [sample_image], output, version="test", run_id="0" * 32)
    assert not output.exists()
    assert not list(tmp_path.glob('.export-*'))


def test_export_preserves_existing_package(tmp_path, sample_image):
    output = tmp_path / "classifier"
    output.mkdir()
    sentinel = output / "existing-weights"
    sentinel.write_bytes(b"keep existing model")
    with pytest.raises(FileExistsError):
        export_package(None, [sample_image], output, version="test", run_id="0" * 32)
    assert sentinel.read_bytes() == b"keep existing model"
