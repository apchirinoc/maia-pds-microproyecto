"""Adaptador del Model Registry de MLflow (respaldado por S3).

Ofrece el contrato que la interfaz necesita para **seleccionar** un modelo ya
versionado en lugar de subir un archivo de pesos: listar las versiones del
registry y activar una fijando el alias `champion`, que es el que el motor de
inferencia carga (`models:/<name>@champion`, ver `app/ml/mlflow_engine.py`).

Dos implementaciones tras un `Protocol`, elegidas por variable de entorno igual
que la inferencia:

- `RegistroSeed`: en memoria, para la demo y las pruebas sin MLflow ni S3.
- `RegistroMLflow`: real, con `mlflow.tracking.MlflowClient`. Lee las metricas del
  run de origen y expone `set_registered_model_alias`. El servidor MLflow es
  parametrizable (`MLFLOW_TRACKING_URI`): el existente o uno nuevo en EC2.

La eleccion vive en `obtener_registro`: si hay `MLFLOW_TRACKING_URI` se usa el
real; si no, el stub.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any, Protocol

from fastapi import Depends

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class VersionModelo:
    """Una versión registrada, agnóstica de si viene de MLflow o del stub."""

    version: str
    alias: str | None
    arch: str
    accuracy: float
    f1: float
    recall: float
    created_at: str
    run_id: str
    artifact_uri: str


class ModeloNoVersionado(LookupError):
    """La versión solicitada no existe en el registry."""


class RegistroModelos(Protocol):
    def listar_versiones(self) -> list[VersionModelo]: ...

    def activar(self, version: str) -> VersionModelo: ...


# --------------------------------------------------------------------------- seed

# Estado en memoria del registry de demostración. Reproduce los dos modelos
# reportados en la Entrega 2 (ResNet18 y CNN simple) más una línea base. El alias
# es mutable para que "activar" sea observable en la misma sesión, igual que el
# catálogo semilla de `repositories/modelos.py` muta `MODELOS`.
_VERSIONES_SEED: list[dict[str, Any]] = [
    {
        "version": "3",
        "arch": "ResNet18_TransferLearning",
        "accuracy": 97.30,
        "f1": 0.9728,
        "recall": 0.9730,
        "created_at": "2026-09-18T15:20:00+00:00",
        "run_id": "seed-run-resnet18",
        "artifact_uri": "s3://brainneuroscan-mlflow/artifacts/3/model",
    },
    {
        "version": "2",
        "arch": "CNN_Simple_Dropout",
        "accuracy": 91.74,
        "f1": 0.9165,
        "recall": 0.9174,
        "created_at": "2026-09-18T15:05:00+00:00",
        "run_id": "seed-run-cnn-dropout",
        "artifact_uri": "s3://brainneuroscan-mlflow/artifacts/2/model",
    },
    {
        "version": "1",
        "arch": "CNN_Simple",
        "accuracy": 88.10,
        "f1": 0.8742,
        "recall": 0.8730,
        "created_at": "2026-09-17T10:00:00+00:00",
        "run_id": "seed-run-cnn-base",
        "artifact_uri": "s3://brainneuroscan-mlflow/artifacts/1/model",
    },
]

_ALIAS_SEED: dict[str, str] = {"champion": "3", "challenger": "2"}


class RegistroSeed(RegistroModelos):
    """Registry en memoria; mantiene la selección de modelos sin MLflow ni S3."""

    def listar_versiones(self) -> list[VersionModelo]:
        version_a_alias = {version: alias for alias, version in _ALIAS_SEED.items()}
        return [
            VersionModelo(
                version=fila["version"],
                alias=version_a_alias.get(fila["version"]),
                arch=fila["arch"],
                accuracy=float(fila["accuracy"]),
                f1=float(fila["f1"]),
                recall=float(fila["recall"]),
                created_at=fila["created_at"],
                run_id=fila["run_id"],
                artifact_uri=fila["artifact_uri"],
            )
            for fila in _VERSIONES_SEED
        ]

    def activar(self, version: str) -> VersionModelo:
        objetivo = next((v for v in self.listar_versiones() if v.version == version), None)
        if objetivo is None:
            raise ModeloNoVersionado(f"No existe la versión {version} en el registry")
        # El campeón anterior pasa a candidato; el objetivo se convierte en campeón.
        anterior = _ALIAS_SEED.get("champion")
        if anterior and anterior != version:
            _ALIAS_SEED["challenger"] = anterior
        _ALIAS_SEED["champion"] = version
        if _ALIAS_SEED.get("challenger") == version:
            del _ALIAS_SEED["challenger"]
        return next(v for v in self.listar_versiones() if v.version == version)


# ------------------------------------------------------------------------- mlflow


class RegistroMLflow(RegistroModelos):
    """Registry real sobre `mlflow.tracking.MlflowClient`.

    No hay preprocesamiento ni pesos aquí: solo se listan versiones y se mueve el
    alias `champion`. Los artefactos viven en S3 y los carga el motor de
    inferencia cuando resuelve `models:/<name>@champion`.
    """

    _METRICAS_F1 = ("test_f1", "test_f1_score")

    def __init__(self, model_name: str, tracking_uri: str) -> None:
        from mlflow.tracking import MlflowClient

        self._name = model_name
        self._cliente = MlflowClient(tracking_uri=tracking_uri)

    def _version_a_alias(self) -> dict[str, str]:
        registrado = self._cliente.get_registered_model(self._name)
        # `aliases` es {alias: version}; se invierte a {version: alias}.
        return {version: alias for alias, version in (registrado.aliases or {}).items()}

    @staticmethod
    def _primera_metrica(metricas: dict[str, Any], claves: tuple[str, ...]) -> float:
        for clave in claves:
            if clave in metricas:
                return float(metricas[clave])
        return 0.0

    def listar_versiones(self) -> list[VersionModelo]:
        alias_por_version = self._version_a_alias()
        versiones: list[VersionModelo] = []
        for mv in self._cliente.search_model_versions(f"name='{self._name}'"):
            metricas: dict[str, Any] = {}
            parametros: dict[str, Any] = {}
            if mv.run_id:
                try:
                    run = self._cliente.get_run(mv.run_id)
                    metricas = run.data.metrics
                    parametros = run.data.params
                except Exception:  # noqa: BLE001 - un run borrado no debe romper el listado
                    pass
            versiones.append(
                VersionModelo(
                    version=str(mv.version),
                    alias=alias_por_version.get(str(mv.version)),
                    arch=str(parametros.get("arch", "")),
                    accuracy=float(metricas.get("test_accuracy", 0.0)),
                    f1=self._primera_metrica(metricas, self._METRICAS_F1),
                    recall=float(metricas.get("test_recall", 0.0)),
                    created_at=(
                        datetime.fromtimestamp(
                            mv.creation_timestamp / 1000, tz=timezone.utc
                        ).isoformat()
                        if mv.creation_timestamp
                        else ""
                    ),
                    run_id=mv.run_id or "",
                    artifact_uri=mv.source or "",
                )
            )
        versiones.sort(
            key=lambda v: int(v.version) if v.version.isdigit() else 0, reverse=True
        )
        return versiones

    def activar(self, version: str) -> VersionModelo:
        try:
            self._cliente.get_model_version(self._name, version)
        except Exception as error:  # noqa: BLE001
            raise ModeloNoVersionado(
                f"No existe la versión {version} de {self._name} en el registry"
            ) from error
        self._cliente.set_registered_model_alias(self._name, "champion", version)
        activada = next((v for v in self.listar_versiones() if v.version == version), None)
        if activada is None:  # pragma: no cover - defensivo
            raise ModeloNoVersionado(f"No se pudo releer la versión {version}")
        return activada


def obtener_registro(
    configuracion: Annotated[Settings, Depends(get_settings)],
) -> RegistroModelos:
    """Elige el registry real o el stub según haya `MLFLOW_TRACKING_URI`."""
    if configuracion.mlflow_tracking_uri:
        return RegistroMLflow(
            configuracion.mlflow_model_name, configuracion.mlflow_tracking_uri
        )
    return RegistroSeed()


RegistroModelosDep = Annotated[RegistroModelos, Depends(obtener_registro)]
