"""Paridad con las transformaciones publicadas en el PR #28, sin reentrenar."""
import io

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
from torchvision import transforms
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
