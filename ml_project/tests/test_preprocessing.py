"""Pruebas del contrato de preprocesamiento."""

from __future__ import annotations

import numpy as np
import pytest

from pipelines.preprocessing import InvalidImageError, MriPreprocessor, PreprocessConfig
from tests.conftest import encode_synthetic_mri


def test_produce_tensor_con_forma_y_tipo_esperados(preprocess_config, sample_image):
    tensor = MriPreprocessor(preprocess_config).from_bytes(sample_image)
    size = preprocess_config.target_size
    assert tensor.shape == (3, size, size)
    assert tensor.dtype == np.float32


def test_es_determinista(preprocess_config, sample_image):
    primero = MriPreprocessor(preprocess_config).from_bytes(sample_image)
    segundo = MriPreprocessor(preprocess_config).from_bytes(sample_image)
    np.testing.assert_array_equal(primero, segundo)


@pytest.mark.parametrize("channels", [1, 3, 4])
def test_acepta_escala_de_grises_rgb_y_rgba(preprocess_config, channels):
    imagen = encode_synthetic_mri(channels=channels)
    tensor = MriPreprocessor(preprocess_config).from_bytes(imagen)
    assert tensor.shape == (3, preprocess_config.target_size, preprocess_config.target_size)


def test_normaliza_entradas_de_16_bits(preprocess_config):
    imagen_16 = np.linspace(0, 65535, 256 * 256, dtype=np.uint16).reshape(256, 256)
    gris = MriPreprocessor.to_uint8_grayscale(imagen_16)
    assert gris.dtype == np.uint8
    assert gris.min() == 0
    assert gris.max() == 255


def test_clahe_modifica_la_imagen(preprocess_config, sample_image):
    """Si CLAHE no se aplicara, el tensor coincidiria con el de clip minimo."""
    sin_realce = PreprocessConfig(clahe_clip_limit=0.01)
    con_realce = MriPreprocessor(preprocess_config).from_bytes(sample_image)
    plano = MriPreprocessor(sin_realce).from_bytes(sample_image)
    assert not np.allclose(con_realce, plano)


def test_rechaza_contenido_no_decodificable(preprocess_config):
    procesador = MriPreprocessor(preprocess_config)
    with pytest.raises(InvalidImageError):
        procesador.from_bytes(b"esto no es una imagen")
    with pytest.raises(InvalidImageError):
        procesador.from_bytes(b"")


def test_la_huella_cambia_con_la_configuracion(preprocess_config):
    assert preprocess_config.fingerprint == PreprocessConfig().fingerprint
    assert preprocess_config.fingerprint != PreprocessConfig(target_size=256).fingerprint
    assert preprocess_config.fingerprint != PreprocessConfig(clahe_clip_limit=3.0).fingerprint


def test_la_etiqueta_se_deriva_de_la_configuracion():
    assert PreprocessConfig().label == "224×224 · CLAHE"
    assert PreprocessConfig(target_size=256).label == "256×256 · CLAHE"


def test_serializacion_de_ida_y_vuelta(preprocess_config):
    restaurada = PreprocessConfig.from_json(preprocess_config.to_json())
    assert restaurada == preprocess_config
    assert restaurada.fingerprint == preprocess_config.fingerprint


def test_configuracion_invalida_falla_al_construirse():
    with pytest.raises(ValueError):
        PreprocessConfig(target_size=0)
    with pytest.raises(ValueError):
        PreprocessConfig(interpolation="nearest")
    with pytest.raises(ValueError):
        PreprocessConfig(std=(0.0, 0.1, 0.1))
