"""Contrato de los endpoints del Model Registry (seleccionar de S3/MLflow).

Se ejecutan con el registry en memoria (`RegistroSeed`), que es lo que hay sin
`MLFLOW_TRACKING_URI`, de modo que no necesitan MLflow ni S3 reales. El contrato
que validan es el mismo que servirá `RegistroMLflow` en producción.
"""

from __future__ import annotations

CAMPOS = {"version", "alias", "arch", "accuracy", "f1", "recall", "createdAt", "runId", "artifactUri"}


async def test_listar_registry_devuelve_versiones(cliente, cabeceras):
    respuesta = await cliente.get("/api/v1/models/registry", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text

    versiones = respuesta.json()
    assert len(versiones) >= 2
    for version in versiones:
        assert CAMPOS.issubset(version.keys())
        assert version["artifactUri"].startswith("s3://")

    campeones = [v for v in versiones if v["alias"] == "champion"]
    assert len(campeones) == 1, "debe haber exactamente un champion"


async def test_activar_fija_champion(cliente, cabeceras):
    activada = await cliente.post("/api/v1/models/registry/2/activate", headers=cabeceras)
    assert activada.status_code == 200, activada.text
    cuerpo = activada.json()
    assert cuerpo["version"] == "2"
    assert cuerpo["alias"] == "champion"

    versiones = (await cliente.get("/api/v1/models/registry", headers=cabeceras)).json()
    por_version = {v["version"]: v for v in versiones}
    assert por_version["2"]["alias"] == "champion"
    assert sum(1 for v in versiones if v["alias"] == "champion") == 1


async def test_activar_version_inexistente_da_404(cliente, cabeceras):
    respuesta = await cliente.post("/api/v1/models/registry/999/activate", headers=cabeceras)
    assert respuesta.status_code == 404


async def test_registry_requiere_autenticacion(cliente):
    assert (await cliente.get("/api/v1/models/registry")).status_code == 401
    assert (await cliente.post("/api/v1/models/registry/2/activate")).status_code == 401
