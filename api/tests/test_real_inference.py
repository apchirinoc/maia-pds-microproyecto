"""Pruebas de integración con un paquete ONNX local, nunca con un simulador de API.

Defina BNS_TEST_MODEL_PACKAGE con el paquete de tests/create_fixture_package.py.
Las credenciales PostgreSQL deben señalar exclusivamente una base desechable.
"""
import hashlib
import io
import os
from dataclasses import replace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image

from tests.conftest import construir_app

PACKAGE = os.environ.get("BNS_TEST_MODEL_PACKAGE")
pytestmark = pytest.mark.skipif(not PACKAGE, reason="Defina BNS_TEST_MODEL_PACKAGE para probar ONNX")


def png(color="white", size=(64, 64)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


@pytest_asyncio.fixture
async def real_client(origen, monkeypatch):
    monkeypatch.setenv("INFERENCE_ENGINE", "onnx")
    monkeypatch.setenv("MLFLOW_MODEL_URI", PACKAGE)
    monkeypatch.setenv("MLFLOW_MODEL_NAME", "synthetic-integration-fixture")
    app = construir_app(origen)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, app
    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker
    if origen == "postgres":
        await get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_bytes_reach_engine_country_cannot_choose_class(real_client, origen):
    client, app = real_client
    content = png()
    expected = app.state.inference_engine.classify([content])[0]
    responses = []
    for country in ("CO", "US", "CO"):
        response = await client.post("/api/v1/classifications", data={"countryCode": country},
                                     files={"file": ("same.png", content, "image/png")})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["predictedClass"] == expected.predicted_class
        assert result["confidenceByClass"] == {s.tumor_class: round(s.confidence * 100, 2) for s in expected.scores}
        assert result["imageSha256"] == hashlib.sha256(content).hexdigest()
        assert result["simulatedInference"] is False
        assert result["persisted"] == (origen == "postgres")
        assert "fixture-1" in result["modelVersion"]
        responses.append(result)
    if origen == "postgres":
        assert len({r["uploadId"] for r in responses}) == 3
        token = (await client.post("/api/v1/auth/login", json={"username": "demo", "password": "demo"})).json()["accessToken"]
        history = await client.get("/api/v1/uploads?pageSize=50", headers={"Authorization": f"Bearer {token}"})
        assert history.status_code == 200, history.text
        row = next(row for row in history.json()["items"] if row["id"] == responses[-1]["uploadId"])
        assert row["simulatedInference"] is False
        assert row["imageSha256"] == responses[-1]["imageSha256"]
        assert row["modelVersion"] == responses[-1]["modelVersion"]
        csv = await client.get("/api/v1/uploads/export", headers={"Authorization": f"Bearer {token}"})
        assert csv.status_code == 200
        assert "simulatedInference,modelVersion,modelUri,preprocessFingerprint,imageSha256" in csv.text
        assert responses[-1]["imageSha256"] in csv.text
        # Reutilizar el pool entre autenticación, agregados y cursor de exportación.
        for _ in range(3):
            await client.get("/api/v1/uploads/summary", headers={"Authorization": f"Bearer {token}"})
            exported = await client.get("/api/v1/uploads/export", headers={"Authorization": f"Bearer {token}"})
            assert responses[-1]["uploadId"] in exported.text


@pytest.mark.asyncio
async def test_catalog_describes_loaded_model_without_inventing_metrics(real_client, origen):
    client, _ = real_client
    info = (await client.get("/api/v1/classifications/model-info")).json()
    assert info["simulatedInference"] is False
    assert info["evaluationMetrics"] == {}
    kpis = (await client.get("/api/v1/dashboard/kpis")).json()
    assert kpis["modelAccuracy"] is None
    if origen == "postgres":
        token = (await client.post("/api/v1/auth/login", json={"username": "demo", "password": "demo"})).json()["accessToken"]
        headers = {"Authorization": f"Bearer {token}"}
        models = (await client.get("/api/v1/models", headers=headers)).json()
        current = next(m for m in models if m["status"] == "production")
        assert current["version"] == "fixture-1"
        assert current["accuracy"] is None
        assert current["dataSource"] == "artifact"
        summary = await client.get("/api/v1/models/summary", headers=headers)
        assert summary.status_code == 200
        assert (await client.get("/api/v1/models/registry", headers=headers)).json() == []
        assert (await client.post("/api/v1/models/registry/1/activate", headers=headers)).status_code == 409


@pytest.mark.asyncio
async def test_catalog_preserves_full_logged_model_identifier(real_client, origen):
    if origen != "postgres":
        pytest.skip("Requiere persistencia")
    from app.db.session import get_sessionmaker
    from app.services.model_catalog import serving_model
    from sqlalchemy import text

    _, app = real_client
    version = "m-994b5e15a2be4cd99280ca696ae54d8f"
    info = replace(app.state.inference_engine.describe(), model_version=version)
    async with get_sessionmaker()() as session:
        model = await serving_model(session, info)
        assert model.version == version
        summary_version = await session.scalar(text(
            "SELECT production_model_version FROM vw_model_registry_summary"
        ))
        assert summary_version == version
        await session.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("content,mime,status", [(b"", "image/png", 422), (b"not an image", "image/png", 422),
                                                   (png(), "image/jpeg", 415), (png(), "text/plain", 415),
                                                   (b"x" * (8 * 1024 * 1024 + 1), "image/png", 413),
                                                   (png(size=(8193, 1)), "image/png", 413)],
                         ids=["empty", "corrupt", "wrong-mime", "unsupported", "too-large", "dimensions"])
async def test_invalid_images_are_rejected(real_client, content, mime, status):
    client, _ = real_client
    response = await client.post("/api/v1/classifications", data={"countryCode": "CO"},
                                 files={"file": ("test.png", content, mime)})
    assert response.status_code == status, response.text


@pytest.mark.asyncio
async def test_no_hint_or_missing_image_and_readiness(real_client):
    client, _ = real_client
    assert (await client.get("/ready")).status_code == 200
    for data in ({"countryCode": "CO"}, {"countryCode": "CO", "hint": "glioma"}, {"countryCode": "XX"}):
        response = await client.post("/api/v1/classifications", data=data)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_engine_failure_never_returns_simulation(real_client, monkeypatch):
    client, app = real_client
    def fail(*args, **kwargs):
        raise RuntimeError("internal model failure")
    monkeypatch.setattr(app.state.inference_engine, "classify", fail)
    response = await client.post("/api/v1/classifications", data={"countryCode": "CO"},
                                 files={"file": ("test.png", png(), "image/png")})
    assert response.status_code == 503
    assert "internal model failure" not in response.text
    assert "predictedClass" not in response.json()


@pytest.mark.asyncio
async def test_storage_failure_is_not_reported_as_success(real_client, origen, monkeypatch):
    if origen != "postgres":
        pytest.skip("Requiere persistencia")
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.exc import SQLAlchemyError
    async def fail(session):
        raise SQLAlchemyError("commit failed")
    monkeypatch.setattr(AsyncSession, "commit", fail)
    client, _ = real_client
    response = await client.post("/api/v1/classifications", data={"countryCode": "CO"},
                                 files={"file": ("test.png", png(), "image/png")})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_unloadable_package_aborts_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("INFERENCE_ENGINE", "onnx")
    monkeypatch.setenv("MLFLOW_MODEL_URI", str(tmp_path / "missing"))
    app = construir_app("seed")
    with pytest.raises(Exception):
        async with app.router.lifespan_context(app):
            pytest.fail("No debe arrancar sin modelo")
