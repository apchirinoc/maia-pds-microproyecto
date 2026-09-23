"""Repositorio del histórico de cargas, de la verdad de campo y de la escritura
de clasificaciones.

Sigue el mismo patrón que `app/repositories/catalogos.py`:

  1. Un `Protocol` que define el contrato, sin saber de dónde salen los datos.
  2. Una implementación `CargasSeed` que lee de `app/seed/` (memoria).
  3. Una implementación `CargasPostgres` que consulta la base con SQLAlchemy.
  4. Una dependencia que elige según `DATA_SOURCE`.

Es el repositorio de los endpoints que **escriben**, así que aquí viven las dos
reglas delicadas del esquema:

* `uq_ground_truth_vigente_por_carga` — índice único parcial sobre
  `deleted_at IS NULL`: registrar una confirmación nueva obliga a marcar la
  anterior con borrado lógico *antes* de insertar, en la misma transacción.
* `uq_predictions_una_por_carga` — una predicción por carga: cada clasificación
  crea su propia carga.

Las agregaciones no se recalculan en Python: se leen de las vistas de
`model/scripts/ddl/10_vistas.sql`, para que exista una sola definición de cada
métrica. Lo que sí ocurre aquí es la conversión de tipos —Postgres devuelve
`Decimal` y los esquemas declaran `float`— y el formato ISO-8601 con sufijo `Z`
que el contrato con el frontend exige.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator, Iterable, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any, Protocol

from fastapi import Depends
from sqlalchemy import Row, Select, and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import get_session_opcional
from app.ml.engine import ModelInfo
from app.services.model_catalog import serving_model
from app.models.entidades import (
    Country,
    DatasetImage,
    GroundTruthDiagnosis,
    Model,
    Prediction,
    PredictionScore,
    Upload,
)
from app.seed.cargas import HISTORICO_CARGAS, RESUMEN_BASE
from app.seed.catalogos import PAISES
from app.seed.modelos import RESUMEN_REGISTRO

CABECERA_CSV = (
    "id,fileName,capturedAt,countryName,prediction,confidence,status,"
    "groundTruth,groundTruthSource,confirmedBy,confirmedAt,isCorrect,"
    "simulatedInference,modelVersion,modelUri,preprocessFingerprint,imageSha256\n"
)

# Filas por lectura del cursor de servidor en la exportación.
TAMANO_LOTE_CSV = 50


def _a_iso(momento: datetime) -> str:
    """ISO-8601 en UTC con milisegundos y sufijo Z, como `Date.toISOString()`.

    Postgres devuelve `datetime` con zona horaria; la semilla ya guarda el texto
    formateado. La conversión vive aquí para que la salida sea idéntica en ambos
    orígenes.
    """
    return (
        momento.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _flotante(valor: Decimal | float | None) -> float | None:
    """Postgres devuelve `Decimal`; los esquemas declaran `float`."""
    return None if valor is None else float(valor)


def _campo_csv(valor: str) -> str:
    """Entrecomilla sólo si hace falta (RFC 4180).

    `confirmed_by` lo escribe una persona y puede traer una coma; el resto de
    columnas viene de catálogos y sale sin comillas, exactamente como antes.
    """
    if any(caracter in valor for caracter in (",", '"', "\n", "\r")):
        return '"' + valor.replace('"', '""') + '"'
    return valor


def _linea_csv(registro: dict[str, Any]) -> str:
    verdad = registro["ground_truth"]
    return (
        ",".join(
            _campo_csv(campo)
            for campo in (
                registro["id"],
                registro["file_name"],
                registro["captured_at"],
                registro["country_name"],
                registro["prediction"],
                str(registro["confidence"]),
                registro["status"],
                verdad["diagnosis"] if verdad else "",
                verdad["source"] if verdad else "",
                verdad["confirmed_by"] if verdad else "",
                verdad["confirmed_at"] if verdad else "",
                # Vacío, no «false», cuando aún no hay diagnóstico confirmado.
                str(verdad["diagnosis"] == registro["prediction"]).lower() if verdad else "",
                str(registro.get("simulated_inference", True)).lower(),
                registro.get("model_version", ""),
                registro.get("model_uri", ""),
                registro.get("preprocess_fingerprint", ""),
                registro.get("image_sha256", ""),
            )
        )
        + "\n"
    )


def calcular_metricas_verdad_campo(registros: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Misma fórmula que la vista `vw_ground_truth_performance` y que el frontend.

    Una carga sin confirmar NO cuenta como fallo: queda fuera del numerador y
    del denominador de la precisión. «Desconocido» no es «error».
    """
    total = len(registros)
    confirmadas = [registro for registro in registros if registro["ground_truth"]]
    aciertos = sum(
        1
        for registro in confirmadas
        if registro["ground_truth"]["diagnosis"] == registro["prediction"]
    )

    return {
        "total_uploads": total,
        "confirmed_uploads": len(confirmadas),
        "correct_predictions": aciertos,
        "mismatched_predictions": len(confirmadas) - aciertos,
        "coverage": 0.0 if total == 0 else len(confirmadas) / total * 100,
        "measured_accuracy": None if not confirmadas else aciertos / len(confirmadas) * 100,
    }


class RepositorioCargas(Protocol):
    async def listar_cargas(
        self, *, clase: str, pagina: int, tamano_pagina: int
    ) -> tuple[list[dict[str, Any]], int]: ...

    async def obtener_resumen(self) -> dict[str, Any]: ...

    def exportar_csv(self) -> AsyncIterator[str]: ...

    async def registrar_verdad_campo(
        self, public_id: str, *, diagnostico: str, confirmado_por: str, fuente: str
    ) -> dict[str, Any] | None: ...

    async def anadir_al_dataset(self, ids: Iterable[str]) -> int: ...

    async def registrar_clasificacion(
        self,
        *,
        codigo_pais: str,
        nombre_archivo: str,
        contenido: bytes | None,
        clase_predicha: str,
        confianzas: dict[str, float],
        etiqueta_preproceso: str,
        simulada: bool,
        modelo_info: ModelInfo | None = None,
        latencia_ms: int | None = None,
    ) -> str | None: ...

    async def codigos_pais(self) -> set[str]: ...

    async def version_modelo_produccion(self) -> str: ...


# ---------------------------------------------------------------------------
# Semilla
# ---------------------------------------------------------------------------


class CargasSeed(RepositorioCargas):
    """Modo demostración: opera sobre las listas en memoria de `app/seed/`."""

    async def listar_cargas(
        self, *, clase: str, pagina: int, tamano_pagina: int
    ) -> tuple[list[dict[str, Any]], int]:
        filtrados = (
            HISTORICO_CARGAS
            if clase == "all"
            else [r for r in HISTORICO_CARGAS if r["prediction"] == clase]
        )
        inicio = (pagina - 1) * tamano_pagina
        return filtrados[inicio : inicio + tamano_pagina], len(filtrados)

    async def obtener_resumen(self) -> dict[str, Any]:
        return {**RESUMEN_BASE, "ground_truth": calcular_metricas_verdad_campo(HISTORICO_CARGAS)}

    async def exportar_csv(self) -> AsyncIterator[str]:
        yield CABECERA_CSV
        for inicio in range(0, len(HISTORICO_CARGAS), TAMANO_LOTE_CSV):
            lote = HISTORICO_CARGAS[inicio : inicio + TAMANO_LOTE_CSV]
            yield "".join(_linea_csv(registro) for registro in lote)

    async def registrar_verdad_campo(
        self, public_id: str, *, diagnostico: str, confirmado_por: str, fuente: str
    ) -> dict[str, Any] | None:
        registro = next((r for r in HISTORICO_CARGAS if r["id"] == public_id), None)
        if registro is None:
            return None

        # La semilla no guarda historial: sustituir la confirmación vigente es
        # pisar el diccionario, que es el equivalente en memoria del borrado
        # lógico que hace la implementación de Postgres.
        registro["ground_truth"] = {
            "diagnosis": diagnostico,
            "confirmed_by": confirmado_por,
            "confirmed_at": _a_iso(datetime.now(timezone.utc)),
            "source": fuente,
        }
        return registro

    async def anadir_al_dataset(self, ids: Iterable[str]) -> int:
        conocidos = {registro["id"] for registro in HISTORICO_CARGAS}
        return len([identificador for identificador in ids if identificador in conocidos])

    async def registrar_clasificacion(self, **_: Any) -> None:
        """Sin base de datos no hay nada que persistir; el contrato no cambia."""
        return None

    async def codigos_pais(self) -> set[str]:
        return {pais["code"] for pais in PAISES}

    async def version_modelo_produccion(self) -> str:
        produccion = RESUMEN_REGISTRO["production_model"]
        return f"{produccion['name']} · {produccion['version']}"


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------


class CargasPostgres(RepositorioCargas):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    # -- Lectura ------------------------------------------------------------

    @staticmethod
    def _consulta_historico() -> Select[Any]:
        """Una sola consulta con joins: carga, predicción, país y verdad vigente.

        Se seleccionan columnas y no entidades ORM a propósito. Devolver `Upload`
        arrastraría sus relaciones (`country`, `prediction`, `ground_truths`) y
        cada fila acabaría resolviendo las suyas: el problema N+1. Así, una
        página son exactamente dos consultas —los datos y el total— sea cual sea
        su tamaño.

        La verdad de campo entra con `LEFT JOIN` restringido a `deleted_at IS
        NULL`, que es justo la fila que el índice único parcial mantiene única,
        de modo que el join no puede duplicar cargas.
        """
        return (
            select(
                Upload.public_id,
                Upload.file_name,
                Upload.created_at,
                Country.name.label("country_name"),
                Prediction.predicted_class,
                Prediction.confidence,
                Prediction.is_simulated,
                Prediction.preprocess_label,
                Prediction.preprocess_fingerprint,
                Model.name.label("model_name"),
                Model.version.label("model_version"),
                Model.mlflow_artifact_uri,
                Upload.checksum_sha256,
                Upload.status,
                GroundTruthDiagnosis.diagnosis,
                GroundTruthDiagnosis.source,
                GroundTruthDiagnosis.confirmed_by,
                GroundTruthDiagnosis.confirmed_at,
            )
            .join(Country, Country.code == Upload.country_code)
            .join(Prediction, Prediction.upload_id == Upload.id)
            .join(Model, Model.id == Prediction.model_id)
            .outerjoin(
                GroundTruthDiagnosis,
                and_(
                    GroundTruthDiagnosis.upload_id == Upload.id,
                    GroundTruthDiagnosis.deleted_at.is_(None),
                ),
            )
            .where(Upload.deleted_at.is_(None))
        )

    @staticmethod
    def _fila_a_registro(fila: Row[Any]) -> dict[str, Any]:
        verdad = (
            {
                "diagnosis": fila.diagnosis,
                "confirmed_by": fila.confirmed_by,
                "confirmed_at": _a_iso(fila.confirmed_at),
                "source": fila.source,
            }
            if fila.diagnosis is not None
            else None
        )
        return {
            "id": fila.public_id,
            "file_name": fila.file_name,
            "captured_at": _a_iso(fila.created_at),
            "country_name": fila.country_name,
            "prediction": fila.predicted_class,
            "confidence": _flotante(fila.confidence),
            "status": fila.status,
            "ground_truth": verdad,
            "simulated_inference": fila.is_simulated,
            "model_version": f"{fila.model_name} · {fila.model_version}",
            "model_uri": fila.mlflow_artifact_uri or "",
            "preprocess": fila.preprocess_label,
            "preprocess_fingerprint": fila.preprocess_fingerprint or "",
            "image_sha256": fila.checksum_sha256,
        }

    async def listar_cargas(
        self, *, clase: str, pagina: int, tamano_pagina: int
    ) -> tuple[list[dict[str, Any]], int]:
        consulta = self._consulta_historico()
        if clase != "all":
            consulta = consulta.where(Prediction.predicted_class == clase)

        total = await self._sesion.scalar(
            select(func.count()).select_from(consulta.subquery())
        )
        filas = await self._sesion.execute(
            consulta.order_by(Upload.created_at.desc())
            .offset((pagina - 1) * tamano_pagina)
            .limit(tamano_pagina)
        )
        return [self._fila_a_registro(fila) for fila in filas], int(total or 0)

    async def obtener_resumen(self) -> dict[str, Any]:
        """Los indicadores salen de las vistas, no de un recuento en Python.

        `vw_upload_history_summary` da la cabecera y `vw_ground_truth_performance`
        los cinco números del circuito de verdad de campo, ya redondeados por la
        propia base.
        """
        cabecera = (
            await self._sesion.execute(
                text(
                    "SELECT total_uploads, pending_review, average_confidence, discarded "
                    "FROM vw_upload_history_summary"
                )
            )
        ).one()
        verdad = (
            await self._sesion.execute(
                text(
                    "SELECT total_uploads, confirmed_uploads, correct_predictions, "
                    "mismatched_predictions, coverage, measured_accuracy "
                    "FROM vw_ground_truth_performance"
                )
            )
        ).one()

        return {
            "total_uploads": int(cabecera.total_uploads),
            "pending_review": int(cabecera.pending_review),
            "average_confidence": _flotante(cabecera.average_confidence) or 0.0,
            "discarded": int(cabecera.discarded),
            "ground_truth": {
                "total_uploads": int(verdad.total_uploads),
                "confirmed_uploads": int(verdad.confirmed_uploads),
                "correct_predictions": int(verdad.correct_predictions),
                "mismatched_predictions": int(verdad.mismatched_predictions),
                "coverage": _flotante(verdad.coverage) or 0.0,
                "measured_accuracy": _flotante(verdad.measured_accuracy),
            },
        }

    async def exportar_csv(self) -> AsyncIterator[str]:
        """Lee con cursor de servidor y emite el CSV por lotes.

        El histórico no se materializa entero: se recorre en particiones y cada
        una se convierte en texto y se suelta.
        """
        resultado = await self._sesion.stream(
            self._consulta_historico().order_by(Upload.created_at.desc())
        )
        yield CABECERA_CSV
        async for particion in resultado.partitions(TAMANO_LOTE_CSV):
            yield "".join(_linea_csv(self._fila_a_registro(fila)) for fila in particion)

    # -- Escritura ----------------------------------------------------------

    async def registrar_verdad_campo(
        self, public_id: str, *, diagnostico: str, confirmado_por: str, fuente: str
    ) -> dict[str, Any] | None:
        """Sustituye la confirmación vigente en una sola transacción.

        `uq_ground_truth_vigente_por_carga` es un índice único parcial sobre
        `deleted_at IS NULL`: no puede haber dos vigentes. Por eso el borrado
        lógico de la anterior se vacía a la base (`flush`) *antes* de insertar la
        nueva; en el orden contrario Postgres rechazaría la inserción. Las dos
        sentencias comparten la transacción que confirma la dependencia de sesión
        al terminar la petición: o entran las dos, o no entra ninguna. La
        confirmación anterior no se borra, queda como historial.
        """
        carga = (
            (
                await self._sesion.scalars(
                    select(Upload)
                    .options(
                        joinedload(Upload.country),
                        selectinload(Upload.prediction),
                        selectinload(Upload.ground_truths),
                    )
                    .where(Upload.public_id == public_id, Upload.deleted_at.is_(None))
                )
            )
            .unique()
            .one_or_none()
        )
        if carga is None:
            return None

        ahora = datetime.now(timezone.utc)
        vigente = carga.ground_truth_vigente
        if vigente is not None:
            vigente.deleted_at = ahora
            await self._sesion.flush()

        self._sesion.add(
            GroundTruthDiagnosis(
                id=uuid.uuid4(),
                upload_id=carga.id,
                diagnosis=diagnostico,
                source=fuente,
                confirmed_by=confirmado_por,
                confirmed_at=ahora,
            )
        )
        await self._sesion.flush()

        prediccion = carga.prediction
        return {
            "id": carga.public_id,
            "file_name": carga.file_name,
            "captured_at": _a_iso(carga.created_at),
            "country_name": carga.country.name,
            "prediction": prediccion.predicted_class if prediccion is not None else None,
            "confidence": _flotante(prediccion.confidence) if prediccion is not None else None,
            "status": carga.status,
            "ground_truth": {
                "diagnosis": diagnostico,
                "confirmed_by": confirmado_por,
                "confirmed_at": _a_iso(ahora),
                "source": fuente,
            },
        }

    async def anadir_al_dataset(self, ids: Iterable[str]) -> int:
        """Marca las cargas y crea su imagen de dataset con la trazabilidad puesta.

        La imagen nace con `source='user_upload'` y `origin_upload_id`, que es lo
        que cierra el ciclo carga → dataset. La clase es el diagnóstico
        confirmado cuando existe; sólo si no lo hay se usa la predicción, porque
        promover una etiqueta sin confirmar es realimentar el modelo con su
        propia salida.
        """
        publicos = list(dict.fromkeys(ids))
        if not publicos:
            return 0

        cargas = (
            (
                await self._sesion.scalars(
                    select(Upload)
                    .options(selectinload(Upload.prediction), selectinload(Upload.ground_truths))
                    .where(Upload.public_id.in_(publicos), Upload.deleted_at.is_(None))
                )
            )
            .unique()
            .all()
        )

        ahora = datetime.now(timezone.utc)
        for carga in cargas:
            if carga.added_to_dataset:
                continue

            verdad = carga.ground_truth_vigente
            if verdad is not None:
                clase = verdad.diagnosis
            elif carga.prediction is not None:
                clase = carga.prediction.predicted_class
            else:
                # Sin etiqueta no hay imagen que añadir.
                continue

            carga.added_to_dataset = True
            self._sesion.add(
                DatasetImage(
                    id=uuid.uuid4(),
                    stable_id=f"user-{carga.public_id}",
                    class_code=clase,
                    split="train",
                    file_name=carga.file_name,
                    storage_path=carga.storage_path,
                    checksum_sha256=carga.checksum_sha256,
                    source="user_upload",
                    origin_upload_id=carga.id,
                    is_showcase=False,
                    added_at=ahora,
                )
            )

        await self._sesion.flush()
        return len(cargas)

    async def registrar_clasificacion(
        self,
        *,
        codigo_pais: str,
        nombre_archivo: str,
        contenido: bytes | None,
        clase_predicha: str,
        confianzas: dict[str, float],
        etiqueta_preproceso: str,
        simulada: bool,
        modelo_info: ModelInfo | None = None,
        latencia_ms: int | None = None,
    ) -> str:
        """Persiste la carga, su predicción y las probabilidades por clase.

        La clase y las probabilidades las produce `app/services/clasificacion.py`;
        aquí sólo se guardan. Las tres filas comparten transacción, de modo que
        nunca queda una predicción sin sus barras de confianza.
        """
        modelo = await serving_model(self._sesion, modelo_info) if modelo_info else await self._modelo_produccion()
        if modelo is None:
            raise ValueError("No hay un modelo al que asociar la predicción")

        ahora = datetime.now(timezone.utc)
        identificador = uuid.uuid4()
        public_id = f"upl_{identificador.hex[:8]}"
        # El binario NO vive en la base de datos: sólo su ruta y su hash.
        checksum = hashlib.sha256(
            contenido if contenido is not None else identificador.bytes
        ).hexdigest()

        self._sesion.add(
            Upload(
                id=identificador,
                public_id=public_id,
                file_name=nombre_archivo,
                storage_path=None,
                checksum_sha256=checksum,
                country_code=codigo_pais,
                status="pending",
                added_to_dataset=False,
                created_at=ahora,
            )
        )

        id_prediccion = uuid.uuid4()
        self._sesion.add(
            Prediction(
                id=id_prediccion,
                upload_id=identificador,
                model_id=modelo.id,
                predicted_class=clase_predicha,
                confidence=Decimal(str(confianzas[clase_predicha])),
                preprocess_label=etiqueta_preproceso,
                preprocess_fingerprint=modelo_info.preprocess_fingerprint if modelo_info else None,
                latency_ms=latencia_ms,
                is_simulated=simulada,
                created_at=ahora,
            )
        )
        for clase, confianza in confianzas.items():
            self._sesion.add(
                PredictionScore(
                    prediction_id=id_prediccion,
                    class_code=clase,
                    confidence=Decimal(str(confianza)),
                )
            )

        await self._sesion.flush()
        # La respuesta sólo anuncia persisted después de confirmar la transacción.
        await self._sesion.commit()
        return public_id

    # -- Apoyo --------------------------------------------------------------

    async def _modelo_produccion(self) -> Model | None:
        return await self._sesion.scalar(
            select(Model).where(Model.status == "production", Model.deleted_at.is_(None))
        )

    async def codigos_pais(self) -> set[str]:
        return set(await self._sesion.scalars(select(Country.code)))

    async def version_modelo_produccion(self) -> str:
        modelo = await self._modelo_produccion()
        if modelo is None:
            produccion = RESUMEN_REGISTRO["production_model"]
            return f"{produccion['name']} · {produccion['version']}"
        return f"{modelo.name} · {modelo.version}"


def obtener_repositorio_cargas(
    sesion: Annotated[AsyncSession | None, Depends(get_session_opcional)],
) -> RepositorioCargas:
    """`sesion` llega como None cuando DATA_SOURCE no es postgres."""
    return CargasSeed() if sesion is None else CargasPostgres(sesion)


RepositorioCargasDep = Annotated[RepositorioCargas, Depends(obtener_repositorio_cargas)]
