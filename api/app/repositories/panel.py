"""Repositorio del panel analítico.

Sigue el mismo patrón que `app/repositories/catalogos.py`:

  1. Un `Protocol` que define el contrato, sin saber de dónde salen los datos.
  2. Una implementación `PanelSeed` que lee de `app/seed/` (memoria).
  3. Una implementación `PanelPostgres` que consulta la base con SQLAlchemy.
  4. Una dependencia que elige según `DATA_SOURCE`.

Las agregaciones pesadas no se recalculan aquí: se leen de las vistas creadas en
`model/scripts/ddl/10_vistas.sql`, para que exista una sola definición de cada
métrica. Lo que sí ocurre en este módulo es la conversión de tipos —Postgres
devuelve `Decimal` y los esquemas declaran `float`/`int`— y el formato de
presentación que el contrato con el frontend exige (iniciales de mes, cadena de
desglose del dataset).
"""

from __future__ import annotations

from typing import Annotated, Any, Protocol

from fastapi import Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.session import get_session_opcional
from app.models.entidades import CLASES_TUMOR, DatasetImage, Model, TumorClassCatalog, Upload
from app.seed.catalogos import CARGAS_POR_PAIS
from app.seed.panel import (
    CARGAS_POR_MES,
    DISTRIBUCION_POR_CLASE,
    KPIS_PANEL,
    MUESTRAS_DATASET,
    PERFIL_CARGAS_RECIENTES,
)

# Iniciales de los meses en español, tal y como las espera el gráfico de barras
# del panel: el esquema `CargasPorMes.month` es un texto de una sola letra.
INICIALES_MES: dict[int, str] = {
    1: "E", 2: "F", 3: "M", 4: "A", 5: "M", 6: "J",
    7: "J", 8: "A", 9: "S", 10: "O", 11: "N", 12: "D",
}

# Meses que muestra el gráfico. La vista `vw_uploads_by_month` no recorta el
# histórico, así que el recorte a los doce últimos se hace aquí.
MESES_VISIBLES = 12

# Días que definen la «ventana reciente» del perfil de cargas.
DIAS_VENTANA_RECIENTE = 30


def formatear_millares(valor: int) -> str:
    """Separa los millares con espacio, como el resto de la interfaz."""
    return f"{valor:,}".replace(",", " ")


def continente_de(latitud: float, longitud: float) -> str:
    """Continente aproximado de un país a partir de sus coordenadas.

    La tabla `countries` sólo guarda latitud y longitud, de modo que el KPI de
    continentes activos se deriva de ellas con rectángulos geográficos. El orden
    de las comprobaciones importa: Asia se evalúa antes que África para que la
    península arábiga (longitud > 40) no caiga en el rectángulo africano.

    Se cuenta América como un único continente, según la convención hispana.
    """
    if longitud >= 110 and latitud <= -10:
        return "Oceanía"
    if latitud >= 36 and -25 <= longitud <= 40:
        return "Europa"
    if longitud > 40:
        return "Asia"
    if -20 <= longitud <= 52:
        return "África"
    if longitud < -25:
        return "América"
    return "Otro"


class RepositorioPanel(Protocol):
    async def obtener_kpis(self) -> dict[str, Any]: ...

    async def obtener_distribucion(self) -> dict[str, int]: ...

    async def listar_cargas_por_pais(self) -> list[dict[str, Any]]: ...

    async def listar_cargas_por_mes(self) -> list[dict[str, Any]]: ...

    async def obtener_perfil_reciente(self) -> list[dict[str, Any]]: ...

    async def listar_muestras_dataset(self) -> list[dict[str, str]]: ...


class PanelSeed(RepositorioPanel):
    """Datos simulados: se devuelven copias, nunca las estructuras originales."""

    async def obtener_kpis(self) -> dict[str, Any]:
        return dict(KPIS_PANEL)

    async def obtener_distribucion(self) -> dict[str, int]:
        return dict(DISTRIBUCION_POR_CLASE)

    async def listar_cargas_por_pais(self) -> list[dict[str, Any]]:
        return [dict(fila) for fila in CARGAS_POR_PAIS]

    async def listar_cargas_por_mes(self) -> list[dict[str, Any]]:
        return [dict(fila) for fila in CARGAS_POR_MES]

    async def obtener_perfil_reciente(self) -> list[dict[str, Any]]:
        return [dict(fila) for fila in PERFIL_CARGAS_RECIENTES]

    async def listar_muestras_dataset(self) -> list[dict[str, str]]:
        return [dict(fila) for fila in MUESTRAS_DATASET]


# --- Consultas sobre las vistas de agregación -------------------------------

_SQL_DISTRIBUCION = text(
    """
    SELECT class_code, total_images, train_images, test_images
    FROM vw_dataset_distribution
    """
)

_SQL_CARGAS_POR_PAIS = text(
    """
    SELECT country_code, country_name, uploads
    FROM vw_uploads_by_country
    """
)

_SQL_CARGAS_POR_MES = text(
    """
    SELECT month_start, uploads
    FROM vw_uploads_by_month
    ORDER BY month_start
    """
)

# Coordenadas de los países que tienen al menos una carga viva: alimentan el
# KPI de continentes activos. La vista `vw_uploads_by_country` no las expone.
_SQL_PAISES_CON_CARGAS = text(
    """
    SELECT c.code, c.latitude, c.longitude
    FROM countries c
    JOIN uploads u ON u.country_code = c.code AND u.deleted_at IS NULL
    GROUP BY c.code, c.latitude, c.longitude
    """
)

# Cargas recientes agrupadas por clase predicha. La ventana se ancla en la carga
# más reciente registrada y no en la fecha de hoy: el conjunto de demostración
# está congelado en el pasado y, medido contra el reloj, el perfil acabaría
# vacío con el paso de las semanas.
_SQL_PERFIL_RECIENTE = text(
    """
    WITH ventana AS (
        SELECT p.predicted_class, p.confidence
        FROM uploads u
        JOIN predictions p ON p.upload_id = u.id
        WHERE u.deleted_at IS NULL
          AND u.created_at >= (
              SELECT max(created_at) FROM uploads WHERE deleted_at IS NULL
          ) - make_interval(days => :dias)
    )
    SELECT predicted_class, count(*) AS cargas, avg(confidence) AS confianza
    FROM ventana
    GROUP BY predicted_class
    """
)


class PanelPostgres(RepositorioPanel):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_kpis(self) -> dict[str, Any]:
        """Compone los ocho indicadores de la cabecera del panel.

        Cada uno sale de una consulta real:

        - `training_images`: filas vivas de `dataset_images`.
        - `training_images_breakdown`: reparto train/test de
          `vw_dataset_distribution`.
        - `model_accuracy`: exactitud del modelo en producción.
        - `model_accuracy_delta_pts`: puntos ganados frente al modelo anterior
          (`previous_model_id`); 0 si el de producción no tiene predecesor.
        - `user_predictions`: total de cargas vivas.
        - `user_predictions_this_month`: cargas del último mes con actividad
          según `vw_uploads_by_month`.
        - `active_countries`: países distintos con cargas.
        - `active_continents`: continentes distintos de esos países.
        """
        distribucion = (await self._sesion.execute(_SQL_DISTRIBUCION)).all()
        imagenes_entrenamiento = sum(int(fila.train_images) for fila in distribucion)
        imagenes_prueba = sum(int(fila.test_images) for fila in distribucion)

        total_imagenes = await self._sesion.scalar(
            select(func.count())
            .select_from(DatasetImage)
            .where(DatasetImage.deleted_at.is_(None))
        )

        # Autojunta `models` consigo misma para traer la exactitud del modelo
        # anterior en la misma consulta. Se piden columnas y no entidades: leer
        # `Model.previous_model` sobre una entidad ya cargada dispararía una
        # carga perezosa fuera del contexto asíncrono.
        modelo_anterior = aliased(Model)
        fila_modelo = (
            await self._sesion.execute(
                select(Model.accuracy, modelo_anterior.accuracy.label("accuracy_anterior"))
                .outerjoin(modelo_anterior, modelo_anterior.id == Model.previous_model_id)
                .where(Model.status == "production", Model.deleted_at.is_(None))
                .limit(1)
            )
        ).first()

        exactitud = float(fila_modelo.accuracy) if fila_modelo is not None and fila_modelo.accuracy is not None else None
        exactitud_anterior = (
            fila_modelo.accuracy_anterior if fila_modelo is not None else None
        )
        delta = (
            round(exactitud - float(exactitud_anterior), 2)
            if exactitud_anterior is not None and exactitud is not None
            else None
        )

        total_cargas = await self._sesion.scalar(
            select(func.count()).select_from(Upload).where(Upload.deleted_at.is_(None))
        )

        meses = (await self._sesion.execute(_SQL_CARGAS_POR_MES)).all()
        cargas_ultimo_mes = int(meses[-1].uploads) if meses else 0

        paises = (await self._sesion.execute(_SQL_PAISES_CON_CARGAS)).all()
        continentes = {
            continente_de(float(pais.latitude), float(pais.longitude)) for pais in paises
        }

        return {
            "training_images": int(total_imagenes or 0),
            "training_images_breakdown": (
                f"{formatear_millares(imagenes_entrenamiento)} train"
                f" · {formatear_millares(imagenes_prueba)} test"
            ),
            "model_accuracy": exactitud,
            "model_accuracy_delta_pts": delta,
            "user_predictions": int(total_cargas or 0),
            "user_predictions_this_month": cargas_ultimo_mes,
            "active_countries": len(paises),
            "active_continents": len(continentes),
        }

    async def obtener_distribucion(self) -> dict[str, int]:
        filas = (await self._sesion.execute(_SQL_DISTRIBUCION)).all()
        totales = {fila.class_code: int(fila.total_images) for fila in filas}
        # Las cuatro claves del esquema son obligatorias: una clase sin imágenes
        # vale cero, no desaparece del donut.
        return {clase: totales.get(clase, 0) for clase in CLASES_TUMOR}

    async def listar_cargas_por_pais(self) -> list[dict[str, Any]]:
        filas = (await self._sesion.execute(_SQL_CARGAS_POR_PAIS)).all()
        return [
            {
                "country_code": fila.country_code,
                "country_name": fila.country_name,
                "uploads": int(fila.uploads),
            }
            for fila in filas
        ]

    async def listar_cargas_por_mes(self) -> list[dict[str, Any]]:
        """La vista devuelve `month_start`; el contrato espera la inicial del mes."""
        filas = (await self._sesion.execute(_SQL_CARGAS_POR_MES)).all()
        return [
            {
                "month": INICIALES_MES[fila.month_start.month],
                "uploads": int(fila.uploads),
            }
            for fila in filas[-MESES_VISIBLES:]
        ]

    async def obtener_perfil_reciente(self) -> list[dict[str, Any]]:
        """Perfil radial de las cargas recientes, normalizado de 0 a 100.

        Ventana: cargas de los últimos `DIAS_VENTANA_RECIENTE` días contados
        desde la carga más reciente registrada.

        Fórmula de cada eje:

        - Una clase: `100 · cargas_de_la_clase / cargas_de_la_clase_dominante`.
          La clase más frecuente de la ventana marca 100 y las demás se leen
          como proporción suya, que es lo que hace legible el radar.
        - `confidence`: media de `predictions.confidence` en la ventana. La
          columna ya está en escala 0-100, así que no se reescala.
        - `volume`: `100 · cargas_de_la_ventana / cargas_históricas`. Mide qué
          parte de toda la actividad del sistema es reciente.

        Todos los valores se redondean a un decimal. Sin cargas en la ventana
        los seis ejes valen 0: el eje debe existir aunque no haya dato.
        """
        filas = (
            await self._sesion.execute(_SQL_PERFIL_RECIENTE, {"dias": DIAS_VENTANA_RECIENTE})
        ).all()

        cargas_por_clase = {fila.predicted_class: int(fila.cargas) for fila in filas}
        cargas_ventana = sum(cargas_por_clase.values())
        clase_dominante = max(cargas_por_clase.values(), default=0)

        confianza_media = (
            sum(float(fila.confianza) * int(fila.cargas) for fila in filas) / cargas_ventana
            if cargas_ventana
            else 0.0
        )

        total_historico = await self._sesion.scalar(
            select(func.count()).select_from(Upload).where(Upload.deleted_at.is_(None))
        )
        volumen = 100.0 * cargas_ventana / total_historico if total_historico else 0.0

        perfil: list[dict[str, Any]] = [
            {
                "axis": clase,
                "value": (
                    round(100.0 * cargas_por_clase.get(clase, 0) / clase_dominante, 1)
                    if clase_dominante
                    else 0.0
                ),
            }
            for clase in CLASES_TUMOR
        ]
        perfil.append({"axis": "confidence", "value": round(confianza_media, 1)})
        perfil.append({"axis": "volume", "value": round(volumen, 1)})
        return perfil

    async def listar_muestras_dataset(self) -> list[dict[str, str]]:
        filas = await self._sesion.execute(
            select(DatasetImage.class_code, DatasetImage.file_name)
            .join(TumorClassCatalog, TumorClassCatalog.code == DatasetImage.class_code)
            .where(DatasetImage.is_showcase.is_(True), DatasetImage.deleted_at.is_(None))
            .order_by(TumorClassCatalog.display_order)
        )
        return [{"tumor_class": clase, "file_name": nombre} for clase, nombre in filas.all()]


def obtener_repositorio_panel(
    sesion: Annotated[AsyncSession | None, Depends(get_session_opcional)],
) -> RepositorioPanel:
    """`sesion` llega como None cuando DATA_SOURCE no es postgres."""
    return PanelSeed() if sesion is None else PanelPostgres(sesion)


RepositorioPanelDep = Annotated[RepositorioPanel, Depends(obtener_repositorio_panel)]
