"""Utilidades compartidas por las pruebas."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper, numpy_helper

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines.config import TUMOR_CLASSES  # noqa: E402
from pipelines.preprocessing import PreprocessConfig  # noqa: E402

RANDOM_SEED = 20260905


def build_dense_onnx_model(destination: Path, config: PreprocessConfig) -> Path:
    """Genera un modelo ONNX valido y sensible a cada pixel de la entrada.

    Aplana la entrada completa y la proyecta con una matriz densa, de modo que
    cualquier diferencia en el preprocesamiento (un pixel distinto) cambia la
    salida. Es lo que convierte la prueba de paridad en una prueba real.
    """
    size = config.target_size
    features = 3 * size * size
    num_classes = len(TUMOR_CLASSES)

    generator = np.random.default_rng(RANDOM_SEED)
    weights = generator.normal(0.0, 1.0 / np.sqrt(features), (num_classes, features)).astype(
        np.float32
    )
    bias = generator.normal(0.0, 0.01, num_classes).astype(np.float32)

    graph = helper.make_graph(
        nodes=[
            helper.make_node("Flatten", ["input"], ["flat"], axis=1),
            helper.make_node("Gemm", ["flat", "W", "B"], ["output"], transB=1),
        ],
        name="tiny_brain_tumor_classifier",
        inputs=[
            helper.make_tensor_value_info("input", TensorProto.FLOAT, [None, 3, size, size])
        ],
        outputs=[
            helper.make_tensor_value_info("output", TensorProto.FLOAT, [None, num_classes])
        ],
        initializer=[
            numpy_helper.from_array(weights, name="W"),
            numpy_helper.from_array(bias, name="B"),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 9
    onnx.checker.check_model(model)

    destination.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(destination))
    return destination


def encode_synthetic_mri(seed: int = RANDOM_SEED, size: int = 320, channels: int = 1) -> bytes:
    """Crea una imagen sintetica con estructura, codificada como PNG.

    No es ruido plano: incluye un fondo oscuro, una elipse brillante y una
    lesion, de modo que CLAHE tenga un histograma real sobre el que actuar.
    """
    generator = np.random.default_rng(seed)
    canvas = np.zeros((size, size), dtype=np.uint8)
    cv2.ellipse(canvas, (size // 2, size // 2), (size // 3, int(size * 0.38)), 0, 0, 360, 140, -1)
    cv2.ellipse(canvas, (size // 2, size // 2), (size // 4, int(size * 0.3)), 0, 0, 360, 90, -1)
    cv2.circle(canvas, (int(size * 0.62), int(size * 0.4)), size // 12, 220, -1)
    noise = generator.integers(0, 18, canvas.shape, dtype=np.uint8)
    canvas = cv2.add(canvas, noise)

    if channels == 3:
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    elif channels == 4:
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGRA)

    success, buffer = cv2.imencode(".png", canvas)
    assert success, "No se pudo codificar la imagen sintetica"
    return buffer.tobytes()


@pytest.fixture(scope="session")
def preprocess_config() -> PreprocessConfig:
    return PreprocessConfig()


@pytest.fixture(scope="session")
def sample_image() -> bytes:
    return encode_synthetic_mri()


@pytest.fixture(scope="session")
def onnx_model_path(tmp_path_factory: pytest.TempPathFactory, preprocess_config) -> Path:
    destination = tmp_path_factory.mktemp("onnx") / "classifier.onnx"
    return build_dense_onnx_model(destination, preprocess_config)
