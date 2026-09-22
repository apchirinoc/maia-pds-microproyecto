"""Histórico de cargas y verdad de campo.

Réplica exacta del generador de `web/src/mocks/uploads.mock.ts`:
mismo generador congruencial, mismas semillas y mismo orden de consumo de
números aleatorios. Así, conectar o desconectar el backend no cambia los datos
que se ven, y la única diferencia observable es el origen que declara la API.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from app.seed.catalogos import CLASES_TUMOR, PAISES

ESTADOS: Final[tuple[str, ...]] = ("validated", "validated", "validated", "pending")

ESPECIALISTAS: Final[tuple[str, ...]] = (
    "dra.moreno@hospital.example",
    "dr.iyer@hospital.example",
    "dr.almeida@hospital.example",
    "dra.rivas@hospital.example",
    "dr.keller@hospital.example",
)

FUENTES_VERDAD_CAMPO: Final[tuple[str, ...]] = (
    "histopathology",
    "radiology_report",
    "follow_up_imaging",
    "specialist_review",
)

TASA_COBERTURA: Final[float] = 0.45
TASA_DISCREPANCIA: Final[float] = 0.18
SEMILLA_VERDAD_CAMPO: Final[int] = 2
SEMILLA_HISTORICO: Final[int] = 42
TOTAL_CARGAS: Final[int] = 120

FECHA_BASE: Final[datetime] = datetime(2026, 8, 23, 8, 41, tzinfo=timezone.utc)

RESUMEN_BASE: Final[dict[str, Any]] = {
    "total_uploads": 12847,
    "pending_review": 214,
    "average_confidence": 94.8,
    "discarded": 37,
}

PREFIJOS: Final[dict[str, str]] = {
    "glioma": "gl",
    "meningioma": "me",
    "pituitary": "pi",
    "healthy": "no",
}


def _generador(semilla: int) -> Callable[[], float]:
    """Mismo generador congruencial lineal que usa el frontend."""
    estado = {"valor": semilla}

    def siguiente() -> float:
        estado["valor"] = (estado["valor"] * 9301 + 49297) % 233280
        return estado["valor"] / 233280

    return siguiente


def _a_iso(momento: datetime) -> str:
    """ISO-8601 en UTC con milisegundos y sufijo Z, como `Date.toISOString()`."""
    return momento.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _construir_historico(total: int) -> list[dict[str, Any]]:
    aleatorio = _generador(SEMILLA_HISTORICO)
    registros: list[dict[str, Any]] = []

    for indice in range(total):
        clase = CLASES_TUMOR[math.floor(aleatorio() * len(CLASES_TUMOR))]
        pais = PAISES[math.floor(aleatorio() * len(PAISES))]
        estado = ESTADOS[math.floor(aleatorio() * len(ESTADOS))]
        # `Math.round` de JS redondea el 0,5 hacia arriba; `round` de Python
        # redondea al par más cercano. Se replica el comportamiento de JS.
        confianza = math.floor((0.82 + aleatorio() * 0.17) * 1000 + 0.5) / 10
        capturada = FECHA_BASE - timedelta(hours=3 * indice)

        registros.append(
            {
                "id": f"upl_{format(0x9F31C4 - indice, 'x')}",
                "file_name": f"Te-{PREFIJOS[clase]}_{str(1000 + indice)[-4:]}.jpg",
                "captured_at": _a_iso(capturada),
                "country_name": pais["name"],
                "prediction": clase,
                "confidence": confianza,
                "status": "validated" if indice < 3 else estado,
                "ground_truth": None,
            }
        )

    return registros


def _clase_discrepante(prediccion: str, sorteo: float) -> str:
    alternativas = [clase for clase in CLASES_TUMOR if clase != prediccion]
    return alternativas[math.floor(sorteo * len(alternativas)) % len(alternativas)]


def _asignar_verdad_campo(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aleatorio = _generador(SEMILLA_VERDAD_CAMPO)

    for indice, registro in enumerate(registros):
        if registro["status"] == "discarded":
            continue
        if aleatorio() > TASA_COBERTURA:
            continue

        discrepa = aleatorio() < TASA_DISCREPANCIA
        diagnostico = (
            _clase_discrepante(registro["prediction"], aleatorio())
            if discrepa
            else registro["prediction"]
        )

        dias_de_espera = 2 + (indice % 8)
        confirmada = datetime.fromisoformat(
            registro["captured_at"].replace("Z", "+00:00")
        ) + timedelta(days=dias_de_espera)

        registro["ground_truth"] = {
            "diagnosis": diagnostico,
            "confirmed_by": ESPECIALISTAS[indice % len(ESPECIALISTAS)],
            "confirmed_at": _a_iso(confirmada),
            "source": FUENTES_VERDAD_CAMPO[indice % len(FUENTES_VERDAD_CAMPO)],
        }

    return registros


HISTORICO_CARGAS: list[dict[str, Any]] = _asignar_verdad_campo(
    _construir_historico(TOTAL_CARGAS)
)
