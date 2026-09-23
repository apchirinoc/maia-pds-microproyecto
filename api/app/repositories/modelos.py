"""Repositorio del registro de modelos.

Sigue el patrón de `app/repositories/catalogos.py`:

  1. Un `Protocol` con el contrato, indiferente al origen de los datos.
  2. Una implementación `...Seed` sobre `app/seed/modelos.py` (memoria).
  3. Una implementación `...Postgres` con SQLAlchemy.
  4. Una dependencia que elige según `DATA_SOURCE`.

El identificador público de un modelo es su `slug` (`effnetb3-bt-v2.4`), no el
uuid: es lo que el frontend guarda en las rutas y lo que la semilla usaba como
`id`. El uuid nunca sale del repositorio.

Los errores de dominio se expresan como excepciones propias
(`ModeloNoEncontrado`, `ConflictoDePromocion`). El repositorio no conoce HTTP;
es el router quien las traduce a 404 y 409.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Any, Protocol

from fastapi import Depends
from sqlalchemy import String, case, cast, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session_opcional
from app.models.entidades import (
    CLASES_TUMOR,
    AuditEvent,
    Model,
    ModelDeployment,
    Prediction,
    User,
)
from app.schemas.auth import SesionAdmin
from app.seed.modelos import DETALLES_MODELO, MODELOS, RESUMEN_REGISTRO

# Eventos del ciclo de vida que este repositorio escribe. Son valores del tipo
# enumerado `deployment_event` del DDL; cualquier otro texto lo rechaza la base.
EVENTO_DESPLIEGUE = "deployedToProduction"
EVENTO_REVERSION = "reverted"
EVENTO_ARCHIVADO = "archived"

# Acción registrada en `audit_events` para cada evento de promoción.
ACCION_AUDITORIA: dict[str, str] = {
    EVENTO_DESPLIEGUE: "model.deploy",
    EVENTO_REVERSION: "model.revert",
}

# Orden de presentación del registro: primero el modelo en producción, después
# los archivados, los que están en validación y por último la línea base. Dentro
# de cada grupo, por exactitud descendente. Reproduce el orden de la semilla, que
# es el que espera la interfaz.
_RANGO_ESTADO: dict[str, int] = {
    "production": 0,
    "archived": 1,
    "validation": 2,
    "baseline": 3,
}


class ModeloNoEncontrado(LookupError):
    """El registro no contiene el modelo o la versión solicitada."""


class ConflictoDePromocion(RuntimeError):
    """Otra promoción ganó la carrera y la base rechazó dejar dos campeones.

    La levanta el índice único parcial `uq_models_un_solo_produccion`. No es un
    error de programación sino una colisión legítima entre dos despliegues
    concurrentes: el router la traduce a 409.
    """


def _flotante(valor: Decimal | float | int | None, por_defecto: float | None = None) -> float | None:
    """Postgres devuelve `Decimal`; los esquemas declaran `float`.

    La conversión vive aquí y no en el esquema para que Pydantic nunca reciba un
    `Decimal` y el contrato del frontend no dependa del tipo del driver.
    """
    return por_defecto if valor is None else float(valor)


def _fecha(valor: date | None) -> str:
    """`active_since` es opcional en la base y obligatorio en el contrato.

    Un modelo que jamás estuvo en producción no tiene fecha; la semilla usa la
    cadena vacía para ese caso y aquí se conserva.
    """
    return "" if valor is None else valor.isoformat()


class RepositorioModelos(Protocol):
    async def listar_modelos(self) -> list[dict[str, Any]]: ...

    async def obtener_resumen(self) -> dict[str, Any] | None: ...

    async def obtener_detalle(self, model_id: str) -> dict[str, Any] | None: ...

    async def desplegar(self, model_id: str, sesion: SesionAdmin) -> None: ...

    async def revertir(
        self, model_id: str, version_objetivo: str, sesion: SesionAdmin
    ) -> None: ...


class ModelosSeed(RepositorioModelos):
    """Registro en memoria. Mantiene la demostración sin base de datos."""

    async def listar_modelos(self) -> list[dict[str, Any]]:
        return list(MODELOS)

    async def obtener_resumen(self) -> dict[str, Any] | None:
        return dict(RESUMEN_REGISTRO)

    async def obtener_detalle(self, model_id: str) -> dict[str, Any] | None:
        return DETALLES_MODELO.get(model_id)

    async def desplegar(self, model_id: str, sesion: SesionAdmin) -> None:
        self._promover(self._buscar(model_id), sesion, EVENTO_DESPLIEGUE)

    async def revertir(
        self, model_id: str, version_objetivo: str, sesion: SesionAdmin
    ) -> None:
        referencia = self._buscar(model_id)
        objetivo = next(
            (
                modelo
                for modelo in MODELOS
                if modelo["name"] == referencia["name"]
                and modelo["version"] == version_objetivo
            ),
            None,
        )
        if objetivo is None:
            raise ModeloNoEncontrado(f"No existe la versión {version_objetivo}")
        self._promover(objetivo, sesion, EVENTO_REVERSION)

    @staticmethod
    def _buscar(model_id: str) -> dict[str, Any]:
        modelo = next((m for m in MODELOS if m["id"] == model_id), None)
        if modelo is None:
            raise ModeloNoEncontrado(f"No existe el modelo {model_id}")
        return modelo

    @staticmethod
    def _promover(
        objetivo: dict[str, Any], sesion: SesionAdmin, etiqueta_evento: str
    ) -> None:
        """Misma secuencia de estados que en Postgres, sobre diccionarios.

        Primero se archiva el campeón vigente y sólo después se promueve el
        objetivo: en memoria el orden es indiferente, pero se conserva para que
        las dos implementaciones se lean igual.
        """
        if objetivo["status"] == "production":
            return

        for modelo in MODELOS:
            if modelo["status"] == "production":
                modelo["status"] = "archived"
                RESUMEN_REGISTRO["archived_versions"] += 1

        objetivo["status"] = "production"
        hoy = date.today().isoformat()

        RESUMEN_REGISTRO["production_model"] = {
            "name": objetivo["name"],
            "version": objetivo["version"],
        }
        RESUMEN_REGISTRO["active_since"] = hoy
        RESUMEN_REGISTRO["accuracy_test"] = objetivo["accuracy"]

        detalle = DETALLES_MODELO.get(objetivo["id"])
        if detalle is not None:
            detalle["status"] = "production"
            detalle["active_since"] = hoy
            detalle["deployment_history"] = [
                {
                    "id": f"evt-{len(detalle['deployment_history']) + 1}",
                    "label": etiqueta_evento,
                    "date": hoy,
                    "author": sesion.username,
                },
                *detalle["deployment_history"],
            ]


class ModelosPostgres(RepositorioModelos):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    # ---------------------------------------------------------------- lectura

    async def listar_modelos(self) -> list[dict[str, Any]]:
        """Sólo las columnas del listado.

        `Model` carga sus relaciones con `selectin`; seleccionar columnas sueltas
        evita traer métricas, matriz de confusión e historial de los cinco
        modelos para pintar una tabla que no los usa.
        """
        # `Model.status` es un ENUM de PostgreSQL. Sin convertirlo a texto, el
        # CASE compara `model_status = character varying` y no existe tal
        # operador: la consulta falla en el servidor.
        orden = case(_RANGO_ESTADO, value=cast(Model.status, String),
                     else_=len(_RANGO_ESTADO))
        filas = await self._sesion.execute(
            select(
                Model.slug,
                Model.name,
                Model.version,
                Model.architecture,
                Model.accuracy,
                Model.f1_macro,
                Model.size_mb,
                Model.status,
                Model.weights_file_name,
                Model.mlflow_artifact_uri,
            )
            .where(Model.deleted_at.is_(None))
            .order_by(orden, Model.accuracy.desc())
        )
        return [
            {
                "id": fila.slug,
                "name": fila.name,
                "version": fila.version,
                "architecture": fila.architecture,
                "accuracy": _flotante(fila.accuracy),
                "f1": _flotante(fila.f1_macro),
                "size_mb": _flotante(fila.size_mb),
                "status": fila.status,
                "weights_file_name": fila.weights_file_name,
                "data_source": "artifact" if fila.mlflow_artifact_uri else "reference",
            }
            for fila in filas
        ]

    async def obtener_resumen(self) -> dict[str, Any] | None:
        """Cabecera del registro, servida por `vw_model_registry_summary`.

        La vista sólo devuelve fila cuando hay un modelo en producción; si el
        registro se queda sin campeón, devuelve `None` y el router responde 404
        en vez de inventar un resumen vacío.
        """
        fila = (
            (
                await self._sesion.execute(
                    text(
                        "SELECT production_model_name, production_model_version, "
                        "active_since, accuracy_test, archived_versions, storage_gb "
                        "FROM vw_model_registry_summary"
                    )
                )
            )
            .mappings()
            .first()
        )
        if fila is None:
            return None

        # La vista no cubre la latencia: se mide sobre las predicciones reales.
        # `predictions.latency_ms` es opcional en el DDL y el histórico cargado
        # todavía no la trae, así que sin mediciones se conserva la referencia de
        # la semilla en lugar de anunciar un engañoso «0 ms».
        latencia = await self._sesion.scalar(select(func.avg(Prediction.latency_ms)))

        return {
            "production_model": {
                "name": fila["production_model_name"],
                "version": fila["production_model_version"],
            },
            "active_since": _fecha(fila["active_since"]),
            "accuracy_test": _flotante(fila["accuracy_test"]),
            "mean_latency_ms": (
                int(round(float(latencia)))
                if latencia is not None
                else None
            ),
            "storage_gb": _flotante(fila["storage_gb"]),
            "archived_versions": int(fila["archived_versions"]),
        }

    async def obtener_detalle(self, model_id: str) -> dict[str, Any] | None:
        # `previous_model` se carga explícitamente: es una relación
        # autorreferencial y recorrerla después de la consulta dispara una carga
        # perezosa que SQLAlchemy rechaza en contexto asíncrono.
        modelo = await self._sesion.scalar(
            select(Model)
            .options(selectinload(Model.previous_model))
            .where(Model.slug == model_id, Model.deleted_at.is_(None))
        )
        if modelo is None:
            return None

        celdas = {
            (celda.actual_class, celda.predicted_class): celda.cell_count
            for celda in modelo.confusion_cells
        }
        f1_por_clase = {
            metrica.class_code: _flotante(metrica.f1) for metrica in modelo.class_metrics
        }
        historial = sorted(
            modelo.deployments, key=lambda evento: evento.event_at, reverse=True
        )

        return {
            "id": modelo.slug,
            "name": modelo.name,
            "version": modelo.version,
            "architecture": modelo.architecture,
            "accuracy": _flotante(modelo.accuracy),
            "f1": _flotante(modelo.f1_macro),
            "size_mb": _flotante(modelo.size_mb),
            "status": modelo.status,
            "weights_file_name": modelo.weights_file_name,
            "data_source": "artifact" if modelo.mlflow_artifact_uri else "reference",
            "training_images": modelo.training_images or 0,
            "test_images": modelo.test_images or 0,
            "active_since": _fecha(modelo.active_since),
            "metrics": {
                "accuracy": _flotante(modelo.accuracy),
                "precision_macro": _flotante(modelo.precision_macro),
                "recall_macro": _flotante(modelo.recall_macro),
                "auc": _flotante(modelo.auc),
            },
            # Las clases se recorren en el orden del catálogo y no en el que
            # devuelva la base: la matriz y las barras por clase se leen mejor
            # cuando las filas aparecen siempre en la misma secuencia.
            "confusion_matrix": {
                real: {
                    predicha: celdas[(real, predicha)]
                    for predicha in CLASES_TUMOR
                    if (real, predicha) in celdas
                }
                for real in CLASES_TUMOR
            },
            "class_performance": {
                clase: f1_por_clase[clase]
                for clase in CLASES_TUMOR
                if clase in f1_por_clase
            },
            "deployment_history": [
                {
                    "id": str(evento.id),
                    "label": evento.event_type,
                    "date": evento.event_at.date().isoformat(),
                    "author": evento.actor_label,
                }
                for evento in historial
            ],
            "target_draft_version": modelo.target_draft_version or "",
            "previous_version": (
                modelo.previous_model.version if modelo.previous_model else None
            ),
        }

    # -------------------------------------------------------------- escritura

    async def desplegar(self, model_id: str, sesion: SesionAdmin) -> None:
        await self._promover(
            await self._buscar_por_slug(model_id), sesion, EVENTO_DESPLIEGUE
        )

    async def revertir(
        self, model_id: str, version_objetivo: str, sesion: SesionAdmin
    ) -> None:
        """Vuelve a otra versión del mismo modelo.

        La versión se busca por (`name`, `version`), que es la clave natural que
        declara `uq_models_nombre_version`; el `slug` de la ruta sólo sirve para
        saber de qué familia de modelos se está hablando.
        """
        referencia = await self._buscar_por_slug(model_id)
        objetivo = await self._sesion.scalar(
            select(Model).where(
                Model.name == referencia.name,
                Model.version == version_objetivo,
                Model.deleted_at.is_(None),
            )
        )
        if objetivo is None:
            raise ModeloNoEncontrado(f"No existe la versión {version_objetivo}")
        await self._promover(objetivo, sesion, EVENTO_REVERSION)

    async def _buscar_por_slug(self, model_id: str) -> Model:
        # `previous_model` se carga aquí de forma explícita. La relación es
        # autorreferencial y su `lazy="selectin"` no se aplica al recorrerla
        # fuera de la consulta: al serializar saltaba una carga perezosa dentro
        # del contexto asíncrono y SQLAlchemy la rechazaba con MissingGreenlet.
        modelo = await self._sesion.scalar(
            select(Model)
            .options(selectinload(Model.previous_model))
            .where(Model.slug == model_id, Model.deleted_at.is_(None))
        )
        if modelo is None:
            raise ModeloNoEncontrado(f"No existe el modelo {model_id}")
        return modelo

    async def _promover(self, objetivo: Model, sesion: SesionAdmin, evento: str) -> None:
        """Promoción atómica: el objetivo pasa a producción y el anterior se archiva.

        EL ORDEN NO ES NEGOCIABLE. `uq_models_un_solo_produccion` es un índice
        único parcial sobre `(status) WHERE status = 'production'`. Los índices
        únicos creados con CREATE UNIQUE INDEX no son aplazables: Postgres los
        comprueba fila a fila, en el instante en que cada fila se escribe, y no
        al confirmar la transacción. Por eso la secuencia es:

          1. Archivar el campeón vigente  → libera la única entrada del índice.
          2. Promover el objetivo         → ocupa la entrada recién liberada.
          3. Anotar los eventos en `model_deployments`.
          4. Anotar la acción en `audit_events`.

        Al revés —promover primero— la fila nueva chocaría con la vieja, que
        todavía está en 'production', y la base rechazaría el UPDATE con
        duplicate key. Tampoco vale resolverlo en una sola sentencia con un CASE
        sobre las dos filas: dentro de un mismo UPDATE el orden en que se
        reescriben las filas no está definido y la comprobación seguiría siendo
        por fila, así que el choque volvería a ser posible.

        Todo ocurre en una única transacción: si falla cualquier paso, ni el
        estado ni la bitácora quedan a medias.
        """
        if objetivo.status == "production":
            return

        ahora = datetime.now(timezone.utc)
        hoy = ahora.date()
        actor_id = await self._sesion.scalar(
            select(User.id).where(
                User.username == sesion.username, User.deleted_at.is_(None)
            )
        )

        # El SELECT ... FOR UPDATE serializa dos despliegues concurrentes sobre
        # la fila del campeón. El segundo en llegar ya no la verá en producción,
        # intentará promover con la entrada del índice ocupada y recibirá el
        # IntegrityError que se traduce en 409: falla uno, no quedan dos.
        anterior = (
            await self._sesion.execute(
                select(Model.id, Model.slug, Model.name, Model.version)
                .where(Model.status == "production", Model.deleted_at.is_(None))
                .with_for_update()
            )
        ).first()

        estado_previo = objetivo.status

        # Paso 1 — archivar. Va antes que nada y se emite como sentencia propia.
        if anterior is not None:
            await self._sesion.execute(
                update(Model)
                .where(Model.id == anterior.id)
                .values(status=EVENTO_ARCHIVADO)
            )
            # El histórico del modelo saliente también merece su línea: la
            # semilla ya registraba un evento `archived` para cada campeón
            # relevado, y el detalle del modelo lo muestra.
            self._sesion.add(
                ModelDeployment(
                    id=uuid.uuid4(),
                    model_id=anterior.id,
                    event_type=EVENTO_ARCHIVADO,
                    event_at=ahora,
                    actor_user_id=actor_id,
                    actor_label=sesion.username,
                    notes=f"Archivado al promover {objetivo.slug}",
                )
            )

        # Paso 2 — promover. Sólo ahora la entrada del índice está libre.
        await self._sesion.execute(
            update(Model)
            .where(Model.id == objetivo.id)
            .values(status="production", active_since=hoy)
        )

        # Paso 3 — el evento del ciclo de vida, con su actor.
        self._sesion.add(
            ModelDeployment(
                id=uuid.uuid4(),
                model_id=objetivo.id,
                event_type=evento,
                event_at=ahora,
                actor_user_id=actor_id,
                actor_label=sesion.username,
                notes=None,
            )
        )

        # Paso 4 — la auditoría. El nivel de riesgo del sistema exige poder
        # responder «quién promovió qué y cuándo» sin leer los registros del
        # servidor, así que se escribe dentro de la misma transacción.
        self._sesion.add(
            AuditEvent(
                id=uuid.uuid4(),
                actor_user_id=actor_id,
                actor_label=sesion.username,
                action=ACCION_AUDITORIA.get(evento, "model.promote"),
                entity_type="model",
                entity_id=objetivo.slug,
                payload={
                    "modelo": objetivo.name,
                    "version": objetivo.version,
                    "evento": evento,
                    "estadoPrevio": estado_previo,
                    "modeloArchivado": anterior.slug if anterior is not None else None,
                    "activoDesde": hoy.isoformat(),
                },
                request_id=None,
                occurred_at=ahora,
            )
        )

        # Se confirma aquí, y no sólo en la dependencia de sesión, para que una
        # colisión con el índice único llegue al endpoint como un 409 y no como
        # un fallo posterior al envío de la respuesta.
        try:
            await self._sesion.commit()
        except IntegrityError as error:
            await self._sesion.rollback()
            raise ConflictoDePromocion(
                "Otra promoción dejó un modelo en producción mientras ésta se "
                "aplicaba; no se ha cambiado nada."
            ) from error


def obtener_repositorio_modelos(
    sesion: Annotated[AsyncSession | None, Depends(get_session_opcional)],
) -> RepositorioModelos:
    """`sesion` llega como None cuando DATA_SOURCE no es postgres."""
    return ModelosSeed() if sesion is None else ModelosPostgres(sesion)


RepositorioModelosDep = Annotated[RepositorioModelos, Depends(obtener_repositorio_modelos)]
