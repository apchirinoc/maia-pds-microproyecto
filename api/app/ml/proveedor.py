"""Ciclo de vida del motor de inferencia: uno por proceso.

Cargar un artefacto de MLflow descarga pesos desde S3, así que el motor se crea
una sola vez y se comparte entre peticiones. En modo simulado no hay motor y
las dependencias devuelven `None`: el endpoint decide entonces el camino simulado.
"""

from __future__ import annotations

import logging
import threading
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.ml.engine import InferenceEngine

logger = logging.getLogger(__name__)


class ProveedorMotor:
    def __init__(self, configuracion: Settings) -> None:
        self._configuracion = configuracion
        self._motor: InferenceEngine | None = None
        self._candado = threading.Lock()

    @property
    def activo(self) -> bool:
        return not self._configuracion.simulated_inference

    def obtener(self) -> InferenceEngine | None:
        if not self.activo:
            return None
        if self._motor is None:
            with self._candado:
                if self._motor is None:
                    self._motor = self._cargar()
        return self._motor

    def recargar(self) -> None:
        """Vuelve a resolver el alias tras activar otra versión.

        El nuevo modelo se carga antes de sustituir al anterior, de modo que las
        peticiones en curso siguen atendidas por el motor que ya estaba cargado.
        """
        if not self.activo:
            return
        motor = self._cargar()
        with self._candado:
            self._motor = motor

    def _cargar(self) -> InferenceEngine:
        import mlflow

        from app.ml.mlflow_engine import MlflowInferenceEngine

        configuracion = self._configuracion
        mlflow.set_tracking_uri(configuracion.mlflow_tracking_uri)
        motor = MlflowInferenceEngine(
            configuracion.mlflow_model_name, alias=configuracion.mlflow_model_alias
        )
        logger.info("Motor de inferencia listo: %s", motor.describe().model_version)
        return motor


def obtener_proveedor(request: Request) -> ProveedorMotor:
    return request.app.state.proveedor_motor


def obtener_motor(
    proveedor: Annotated[ProveedorMotor, Depends(obtener_proveedor)],
) -> InferenceEngine | None:
    return proveedor.obtener()


ProveedorMotorDep = Annotated[ProveedorMotor, Depends(obtener_proveedor)]
MotorInferenciaDep = Annotated[InferenceEngine | None, Depends(obtener_motor)]
