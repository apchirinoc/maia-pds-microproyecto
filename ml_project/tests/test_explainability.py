"""Pruebas del patron «Explainable Predictions».

Dos bloques:

1. El metodo en si (`pipelines/explainability.py`), contra un modelo ONNX
   sintetico que **solo mira una region conocida** de la imagen. Eso permite
   afirmar algo fuerte: el mapa senala exactamente la senal que mueve la
   prediccion, y no una region cualquiera.
2. La integracion en el artefacto: la explicacion viaja dentro del modelo, se
   pide con `params={"explain": True}` y, sin ese parametro, la salida es la
   misma de siempre.
"""

from __future__ import annotations

from pathlib import Path

import mlflow
import numpy as np
import onnx
import onnxruntime as ort
import pandas as pd
import pytest
from onnx import TensorProto, helper, numpy_helper

from pipelines.config import TUMOR_CLASSES
from pipelines.explainability import (
    INFLUENCE_MAP_MEDIA_TYPE,
    OCCLUSION_METHOD_ID,
    OcclusionConfig,
    compute_occlusion_map,
    decode_influence_map,
    encode_influence_map,
    influence_map_data_uri,
)
from pipelines.model_wrapper import (
    EXPLAIN_PARAM,
    EXPLAIN_PATCH_SIZE_PARAM,
    EXPLAIN_STRIDE_PARAM,
    EXPLANATION_COLUMN,
    EXPLANATION_METHOD_COLUMN,
    EXPLANATION_METHOD_LABEL_COLUMN,
    IMAGE_COLUMN,
)
from pipelines.packaging import log_classifier, predict_probabilities, predict_with_explanation
from pipelines.preprocessing import MriPreprocessor
from tests.conftest import encode_synthetic_mri

# Region que el modelo sintetico mira: fila y columna iniciales, y lado.
REGION_TOP = 96
REGION_LEFT = 96
REGION_SIDE = 32
SIGNAL_VALUE = 3.0


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=1, keepdims=True)


def _class_probability(session: ort.InferenceSession, tensor: np.ndarray, index: int) -> float:
    entrada = session.get_inputs()[0].name
    salida = np.asarray(session.run(None, {entrada: tensor[np.newaxis]})[0], dtype=np.float32)
    return float(_softmax(salida)[0, index])


def build_localized_onnx_model(destination: Path, size: int) -> Path:
    """Modelo ONNX cuya clase 0 depende **solo** de una region concreta.

    Los pesos son cero en todas partes menos en el cuadrado
    `[REGION_TOP, REGION_TOP+REGION_SIDE) x [REGION_LEFT, REGION_LEFT+REGION_SIDE)`.
    Es el control que convierte la prueba de localizacion en una afirmacion
    verificable: sabemos de antemano donde esta la evidencia.
    """
    num_classes = len(TUMOR_CLASSES)
    mask = np.zeros((3, size, size), dtype=np.float32)
    mask[:, REGION_TOP : REGION_TOP + REGION_SIDE, REGION_LEFT : REGION_LEFT + REGION_SIDE] = 1.0

    weights = np.zeros((num_classes, 3 * size * size), dtype=np.float32)
    weights[0] = mask.reshape(-1) / float(mask.sum())
    bias = np.zeros(num_classes, dtype=np.float32)

    graph = helper.make_graph(
        nodes=[
            helper.make_node("Flatten", ["input"], ["flat"], axis=1),
            helper.make_node("Gemm", ["flat", "W", "B"], ["output"], transB=1),
        ],
        name="localized_classifier",
        inputs=[helper.make_tensor_value_info("input", TensorProto.FLOAT, [None, 3, size, size])],
        outputs=[helper.make_tensor_value_info("output", TensorProto.FLOAT, [None, num_classes])],
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


@pytest.fixture(scope="module")
def localized_session(tmp_path_factory, preprocess_config) -> ort.InferenceSession:
    path = build_localized_onnx_model(
        tmp_path_factory.mktemp("onnx-localizado") / "localized.onnx",
        preprocess_config.target_size,
    )
    return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])


@pytest.fixture(scope="module")
def localized_tensor(preprocess_config) -> np.ndarray:
    """Tensor con la senal justo donde el modelo sintetico la busca."""
    size = preprocess_config.target_size
    tensor = np.zeros((3, size, size), dtype=np.float32)
    tensor[:, REGION_TOP : REGION_TOP + REGION_SIDE, REGION_LEFT : REGION_LEFT + REGION_SIDE] = (
        SIGNAL_VALUE
    )
    return tensor


def _inside_region(mapa: np.ndarray) -> np.ndarray:
    return mapa[REGION_TOP : REGION_TOP + REGION_SIDE, REGION_LEFT : REGION_LEFT + REGION_SIDE]


# --------------------------------------------------------------------------
# 1. El metodo de explicabilidad
# --------------------------------------------------------------------------


def test_el_mapa_tiene_la_forma_y_el_rango_declarados(
    localized_session, localized_tensor, preprocess_config
):
    mapa = compute_occlusion_map(localized_tensor, localized_session, 0)

    size = preprocess_config.target_size
    assert mapa.shape == (size, size), "El mapa debe cubrir la imagen de entrada completa"
    assert mapa.dtype == np.float32
    assert float(mapa.min()) >= 0.0
    assert float(mapa.max()) == pytest.approx(1.0)


def test_el_mapa_es_determinista(localized_session, localized_tensor):
    """Sin determinismo la explicacion no seria auditable."""
    primero = compute_occlusion_map(localized_tensor, localized_session, 0)
    segundo = compute_occlusion_map(localized_tensor, localized_session, 0)

    assert np.array_equal(primero, segundo)


def test_el_tamano_del_lote_no_altera_el_resultado(localized_session, localized_tensor):
    """El troceado en lotes es una optimizacion de coste, no un cambio de metodo."""
    por_uno = compute_occlusion_map(
        localized_tensor, localized_session, 0, config=OcclusionConfig(batch_size=1)
    )
    por_lotes = compute_occlusion_map(
        localized_tensor, localized_session, 0, config=OcclusionConfig(batch_size=64)
    )

    np.testing.assert_allclose(por_uno, por_lotes, rtol=1e-5, atol=1e-6)


def test_la_region_mas_influyente_es_la_que_mueve_la_prediccion(
    localized_session, localized_tensor
):
    """Afirmacion central: el mapa senala la senal real, no un lugar cualquiera.

    Se comprueba primero que el modelo sintetico se comporta como se espera
    (tapar la region derrumba la probabilidad; tapar otra region no la mueve) y
    despues que el mapa lo refleja.
    """
    base = _class_probability(localized_session, localized_tensor, 0)

    tapando_la_senal = localized_tensor.copy()
    tapando_la_senal[
        :, REGION_TOP : REGION_TOP + REGION_SIDE, REGION_LEFT : REGION_LEFT + REGION_SIDE
    ] = 0.0
    sin_senal = _class_probability(localized_session, tapando_la_senal, 0)

    tapando_otra_zona = localized_tensor.copy()
    tapando_otra_zona[:, 0:REGION_SIDE, 0:REGION_SIDE] = 0.0
    con_otra_zona_tapada = _class_probability(localized_session, tapando_otra_zona, 0)

    assert base - sin_senal > 0.5, "El control no sirve: tapar la senal apenas mueve la prediccion"
    assert con_otra_zona_tapada == pytest.approx(base, abs=1e-6)

    mapa = compute_occlusion_map(localized_tensor, localized_session, 0)
    fila, columna = np.unravel_index(int(np.argmax(mapa)), mapa.shape)

    assert REGION_TOP <= fila < REGION_TOP + REGION_SIDE
    assert REGION_LEFT <= columna < REGION_LEFT + REGION_SIDE

    filas, columnas = np.indices(mapa.shape)
    masa = float(mapa.sum())
    centro_filas = float((mapa * filas).sum() / masa)
    centro_columnas = float((mapa * columnas).sum() / masa)

    assert centro_filas == pytest.approx(REGION_TOP + REGION_SIDE / 2, abs=3.0)
    assert centro_columnas == pytest.approx(REGION_LEFT + REGION_SIDE / 2, abs=3.0)


def test_las_regiones_irrelevantes_no_reciben_influencia(localized_session, localized_tensor):
    mapa = compute_occlusion_map(localized_tensor, localized_session, 0)

    lejos = mapa[0:REGION_SIDE, 0:REGION_SIDE]
    assert float(lejos.max()) == pytest.approx(0.0, abs=1e-6)
    assert float(_inside_region(mapa).mean()) > 10.0 * float(mapa.mean())


def test_un_modelo_ciego_a_la_imagen_produce_un_mapa_vacio(
    tmp_path_factory, preprocess_config, localized_tensor
):
    """Control negativo: sin evidencia espacial, no se inventa una explicacion."""
    size = preprocess_config.target_size
    num_classes = len(TUMOR_CLASSES)
    graph = helper.make_graph(
        nodes=[
            helper.make_node("Flatten", ["input"], ["flat"], axis=1),
            helper.make_node("Gemm", ["flat", "W", "B"], ["output"], transB=1),
        ],
        name="constant_classifier",
        inputs=[helper.make_tensor_value_info("input", TensorProto.FLOAT, [None, 3, size, size])],
        outputs=[helper.make_tensor_value_info("output", TensorProto.FLOAT, [None, num_classes])],
        initializer=[
            numpy_helper.from_array(
                np.zeros((num_classes, 3 * size * size), dtype=np.float32), name="W"
            ),
            numpy_helper.from_array(np.array([2.0, 0.0, 0.0, 0.0], dtype=np.float32), name="B"),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 9
    destination = tmp_path_factory.mktemp("onnx-ciego") / "constant.onnx"
    onnx.save(model, str(destination))

    session = ort.InferenceSession(str(destination), providers=["CPUExecutionProvider"])
    mapa = compute_occlusion_map(localized_tensor, session, 0)

    assert not mapa.any(), "Un modelo insensible a la imagen no puede tener regiones influyentes"


def test_el_coste_de_la_explicacion_esta_acotado(preprocess_config):
    config = OcclusionConfig()
    size = preprocess_config.target_size

    assert config.offsets(size) == tuple(range(0, size - config.patch_size + 1, config.stride))
    assert config.passes_for(size, size) == 169
    assert config.passes_for(size, size) <= config.max_passes


def test_la_rejilla_cubre_el_borde_aunque_no_encaje():
    config = OcclusionConfig(patch_size=32, stride=16)
    offsets = config.offsets(200)

    assert offsets[0] == 0
    assert offsets[-1] == 200 - 32, "La ultima posicion debe alcanzar el borde de la imagen"


def test_se_rechaza_una_configuracion_desmedida(localized_session, localized_tensor):
    with pytest.raises(ValueError, match="pasadas por imagen"):
        compute_occlusion_map(
            localized_tensor,
            localized_session,
            0,
            config=OcclusionConfig(patch_size=16, stride=4, max_passes=64),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"patch_size": 0},
        {"stride": 0},
        {"patch_size": 16, "stride": 32},
        {"batch_size": 0},
        {"max_passes": 0},
    ],
)
def test_la_configuracion_valida_sus_parametros(kwargs):
    with pytest.raises(ValueError):
        OcclusionConfig(**kwargs)


def test_la_serializacion_conserva_el_mapa(localized_session, localized_tensor):
    mapa = compute_occlusion_map(localized_tensor, localized_session, 0)
    recuperado = decode_influence_map(encode_influence_map(mapa))

    assert recuperado.shape == mapa.shape
    # Unica perdida admitida: la cuantizacion a 8 bits del canal alfa.
    np.testing.assert_allclose(recuperado, mapa, atol=1.0 / 255.0)


def test_el_data_uri_es_consumible_por_el_navegador(localized_session, localized_tensor):
    codificado = encode_influence_map(
        compute_occlusion_map(localized_tensor, localized_session, 0)
    )
    uri = influence_map_data_uri(codificado)

    assert uri.startswith(f"data:{INFLUENCE_MAP_MEDIA_TYPE};base64,")
    assert uri.endswith(codificado)


# --------------------------------------------------------------------------
# 2. La explicacion viaja dentro del artefacto
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def logged_model(tmp_path_factory, onnx_model_path, sample_image, preprocess_config):
    workspace = tmp_path_factory.mktemp("mlflow-explicabilidad")
    mlflow.set_tracking_uri(f"sqlite:///{workspace / 'mlflow.db'}")
    artifacts = workspace / "artifacts"
    artifacts.mkdir()
    experiment_id = mlflow.create_experiment(
        "explainable-predictions", artifact_location=artifacts.as_uri()
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


def test_la_firma_declara_el_parametro_explain(logged_model):
    firma = mlflow.models.Model.load(logged_model.model_uri).signature

    assert firma.params is not None, "Sin params en la firma el servicio no puede pedir explicacion"
    declarados = {spec.name: spec.default for spec in firma.params.params}
    assert declarados[EXPLAIN_PARAM] is False, "La explicacion debe ser opcional y estar apagada"
    assert EXPLAIN_PATCH_SIZE_PARAM in declarados
    assert EXPLAIN_STRIDE_PARAM in declarados
    assert [columna.name for columna in firma.outputs.inputs] == list(TUMOR_CLASSES)


def test_los_metadatos_declaran_el_metodo_de_explicabilidad(logged_model):
    metadata = mlflow.models.Model.load(logged_model.model_uri).metadata

    assert metadata["explanation_method"] == OCCLUSION_METHOD_ID
    assert metadata["explanation"]["patch_size"] == OcclusionConfig().patch_size
    assert metadata["explanation"]["stride"] == OcclusionConfig().stride


def test_el_codigo_de_explicabilidad_viaja_dentro_del_artefacto(logged_model):
    local_path = Path(mlflow.artifacts.download_artifacts(logged_model.model_uri))

    assert (local_path / "code" / "pipelines" / "explainability.py").is_file(), (
        "El metodo de explicabilidad debe viajar con el modelo: si lo implementara "
        "el servicio, explicaria un modelo distinto del que sirve"
    )


def test_sin_explain_la_salida_no_cambia(logged_model, onnx_model_path, preprocess_config):
    """Garantia de no regresion: el camino de siempre sigue siendo el de siempre."""
    imagenes = [encode_synthetic_mri(seed=seed) for seed in (7, 8)]

    procesador = MriPreprocessor(preprocess_config)
    sesion = ort.InferenceSession(str(onnx_model_path), providers=["CPUExecutionProvider"])
    entrada = sesion.get_inputs()[0].name
    esperado = _softmax(sesion.run(None, {entrada: procesador.batch(imagenes)})[0])

    servido = mlflow.pyfunc.load_model(logged_model.model_uri)
    frame = pd.DataFrame({IMAGE_COLUMN: imagenes})
    sin_params = servido.predict(frame)
    con_explain_apagado = servido.predict(frame, params={EXPLAIN_PARAM: False})

    assert list(sin_params.columns) == list(TUMOR_CLASSES), "No debe aparecer ninguna columna extra"
    assert list(con_explain_apagado.columns) == list(TUMOR_CLASSES)
    np.testing.assert_allclose(sin_params.to_numpy(), esperado, rtol=1e-6, atol=1e-7)
    np.testing.assert_allclose(con_explain_apagado.to_numpy(), sin_params.to_numpy())
    np.testing.assert_allclose(
        predict_probabilities(servido, imagenes), esperado, rtol=1e-6, atol=1e-7
    )


def test_con_explain_el_artefacto_devuelve_el_mapa(logged_model, preprocess_config):
    imagenes = [encode_synthetic_mri(seed=41), encode_synthetic_mri(seed=42)]
    servido = mlflow.pyfunc.load_model(logged_model.model_uri)

    resultado = predict_with_explanation(servido, imagenes)

    assert list(resultado.columns) == [
        *TUMOR_CLASSES,
        EXPLANATION_COLUMN,
        EXPLANATION_METHOD_COLUMN,
        EXPLANATION_METHOD_LABEL_COLUMN,
    ]
    assert len(resultado) == len(imagenes)

    probabilidades = resultado[list(TUMOR_CLASSES)].to_numpy()
    np.testing.assert_allclose(probabilidades.sum(axis=1), 1.0, rtol=1e-6)

    size = preprocess_config.target_size
    for _, fila in resultado.iterrows():
        assert fila[EXPLANATION_METHOD_COLUMN] == OCCLUSION_METHOD_ID
        assert fila[EXPLANATION_METHOD_LABEL_COLUMN] == OcclusionConfig().label
        mapa = decode_influence_map(str(fila[EXPLANATION_COLUMN]))
        assert mapa.shape == (size, size)
        assert float(mapa.min()) >= 0.0
        assert float(mapa.max()) <= 1.0


def test_la_explicacion_del_artefacto_es_determinista(logged_model):
    imagenes = [encode_synthetic_mri(seed=55)]
    servido = mlflow.pyfunc.load_model(logged_model.model_uri)

    primero = predict_with_explanation(servido, imagenes)[EXPLANATION_COLUMN].iloc[0]
    segundo = predict_with_explanation(servido, imagenes)[EXPLANATION_COLUMN].iloc[0]

    assert primero == segundo


def test_el_servicio_puede_ajustar_la_resolucion_sin_reempaquetar(logged_model, preprocess_config):
    """`params` permite negociar coste y resolucion en tiempo de peticion."""
    servido = mlflow.pyfunc.load_model(logged_model.model_uri)
    frame = pd.DataFrame({IMAGE_COLUMN: [encode_synthetic_mri(seed=61)]})

    grueso = servido.predict(
        frame,
        params={EXPLAIN_PARAM: True, EXPLAIN_PATCH_SIZE_PARAM: 64, EXPLAIN_STRIDE_PARAM: 32},
    )
    mapa = decode_influence_map(str(grueso[EXPLANATION_COLUMN].iloc[0]))

    assert grueso[EXPLANATION_METHOD_LABEL_COLUMN].iloc[0] == "Oclusión 64 px · paso 32 px"
    assert mapa.shape == (preprocess_config.target_size, preprocess_config.target_size)
