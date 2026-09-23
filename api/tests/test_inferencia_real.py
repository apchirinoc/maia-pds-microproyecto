"""Camino de inferencia real (`INFERENCE_ENGINE=onnx`) con un motor falso.

El motor de MLflow se sustituye por un doble que cumple el contrato
`InferenceEngine`: así se valida la traducción al esquema del tablero sin
descargar un artefacto de S3.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.ml.engine import ClassScore, InferenceResult, ModelInfo, PredictionExplanation
from app.ml.proveedor import obtener_motor, obtener_proveedor
from tests.conftest import construir_app

IMAGEN = b"\x89PNG-sintetico"
VERSION = "brain-tumor-classifier · v7"
ETIQUETA = "224×224 · CLAHE (clip 2.0)"


class MotorFalso:
    def __init__(self, *, explica: bool = True) -> None:
        self.explica = explica
        self.llamadas: list[tuple[list[bytes], bool]] = []

    def describe(self) -> ModelInfo:
        return ModelInfo(
            model_version=VERSION,
            preprocess_label=ETIQUETA,
            preprocess_fingerprint="huella",
            classes=("glioma", "meningioma", "pituitary", "healthy"),
            simulated=False,
            explanation_method="occlusion",
            explanation_label="Oclusión 32 px · paso 16 px",
            supports_explanation=self.explica,
        )

    def classify(self, images: Sequence[bytes], *, explain: bool = False) -> list[InferenceResult]:
        self.llamadas.append((list(images), explain))
        puntajes = (
            ClassScore("glioma", 0.91234),
            ClassScore("meningioma", 0.05),
            ClassScore("pituitary", 0.03),
            ClassScore("healthy", 0.00766),
        )
        explicacion = (
            PredictionExplanation("occlusion", "Oclusión 32 px · paso 16 px", "iVBORw0KGgo=")
            if explain
            else None
        )
        return [
            InferenceResult("glioma", puntajes, VERSION, ETIQUETA, explanation=explicacion)
            for _ in images
        ]


class ProveedorFalso:
    def __init__(self) -> None:
        self.recargas = 0

    def recargar(self) -> None:
        self.recargas += 1


async def _cliente(motor: MotorFalso, proveedor: ProveedorFalso | None = None):
    app = construir_app("seed")
    app.dependency_overrides[obtener_motor] = lambda: motor
    if proveedor is not None:
        app.dependency_overrides[obtener_proveedor] = lambda: proveedor
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://pruebas")


@pytest_asyncio.fixture
async def motor() -> MotorFalso:
    return MotorFalso()


@pytest_asyncio.fixture
async def cliente_real(motor: MotorFalso) -> AsyncIterator[AsyncClient]:
    async with await _cliente(motor) as cliente:
        yield cliente


async def test_clasifica_con_el_motor_y_convierte_a_porcentajes(cliente_real, motor):
    respuesta = await cliente_real.post(
        "/api/v1/classifications",
        data={"countryCode": "CO", "explain": "true"},
        files={"file": ("mri.png", IMAGEN, "image/png")},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert motor.llamadas == [([IMAGEN], True)]
    assert cuerpo["predictedClass"] == "glioma"
    assert cuerpo["confidenceByClass"] == {
        "glioma": 91.2,
        "meningioma": 5.0,
        "pituitary": 3.0,
        "healthy": 0.8,
    }
    assert cuerpo["modelVersion"] == VERSION
    assert cuerpo["preprocess"] == ETIQUETA
    assert cuerpo["explanation"]["method"] == "occlusion"
    assert cuerpo["explanation"]["influenceMapDataUri"] == "data:image/png;base64,iVBORw0KGgo="


async def test_la_pista_no_altera_la_prediccion_real(cliente_real):
    respuesta = await cliente_real.post(
        "/api/v1/classifications",
        data={"countryCode": "CO", "hint": "healthy"},
        files={"file": ("mri.png", IMAGEN, "image/png")},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["predictedClass"] == "glioma"


async def test_inferencia_real_exige_archivo(cliente_real, motor):
    respuesta = await cliente_real.post(
        "/api/v1/classifications", data={"countryCode": "CO", "hint": "glioma"}
    )
    assert respuesta.status_code == 422
    assert motor.llamadas == []


async def test_sin_explicacion_si_el_modelo_no_la_declara():
    motor = MotorFalso(explica=False)
    async with await _cliente(motor) as cliente:
        respuesta = await cliente.post(
            "/api/v1/classifications",
            data={"countryCode": "CO", "explain": "true"},
            files={"file": ("mri.png", IMAGEN, "image/png")},
        )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["explanation"] is None
    assert motor.llamadas == [([IMAGEN], False)]


async def test_model_info_y_meta_describen_el_modelo_real(cliente_real):
    info = (await cliente_real.get("/api/v1/classifications/model-info")).json()
    assert info == {"modelVersion": VERSION, "preprocessLabel": ETIQUETA, "simulatedInference": False}

    meta = (await cliente_real.get("/api/v1/meta")).json()
    assert meta["simulatedInference"] is False
    assert meta["modelVersion"] == VERSION
    assert meta["preprocessLabel"] == ETIQUETA


async def test_activar_una_version_recarga_el_motor(motor):
    proveedor = ProveedorFalso()
    async with await _cliente(motor, proveedor) as cliente:
        login = await cliente.post(
            "/api/v1/auth/login", json={"username": "demo", "password": "demo"}
        )
        cabeceras = {"Authorization": f"Bearer {login.json()['accessToken']}"}
        respuesta = await cliente.post("/api/v1/models/registry/3/activate", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert proveedor.recargas == 1


def test_proveedor_carga_una_vez_y_recarga_bajo_demanda(monkeypatch):
    from app.core.config import Settings
    from app.ml.proveedor import ProveedorMotor

    cargas: list[MotorFalso] = []

    def cargar(_self):
        cargas.append(MotorFalso())
        return cargas[-1]

    monkeypatch.setattr(ProveedorMotor, "_cargar", cargar)
    proveedor = ProveedorMotor(
        Settings(_env_file=None, inference_engine="onnx", mlflow_tracking_uri="http://mlflow")
    )

    primero = proveedor.obtener()
    assert proveedor.obtener() is primero
    proveedor.recargar()
    assert proveedor.obtener() is cargas[1]
    assert len(cargas) == 2

    simulado = ProveedorMotor(Settings(_env_file=None, inference_engine="simulated"))
    simulado.recargar()
    assert simulado.obtener() is None


def test_onnx_sin_tracking_uri_no_arranca():
    from app.core.config import Settings

    with pytest.raises(ValidationError, match="MLFLOW_TRACKING_URI"):
        Settings(_env_file=None, inference_engine="onnx", mlflow_tracking_uri="")
