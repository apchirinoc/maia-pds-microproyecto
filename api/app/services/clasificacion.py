"""Inferencia simulada del servidor.

Réplica del generador de `web/src/mocks/classification.mock.ts`:
mismas funciones hash y pseudoaleatorias, misma geometría de la lesión y mismo
SVG de salida. Conectar el backend no cambia lo que se ve; sólo cambia de dónde
viene.

Cuando `INFERENCE_ENGINE=onnx`, este módulo se sustituye por el adaptador de
MLflow (`app/ml/mlflow_engine.py`), que además devuelve el mapa calculado por
oclusión sobre el artefacto real.
"""

from __future__ import annotations

import math
import random as _random
from collections.abc import Callable
from typing import Any, Final
from urllib.parse import quote

CLASES_TUMOR: Final[tuple[str, ...]] = ("glioma", "meningioma", "pituitary", "healthy")

DESCRIPCIONES: Final[dict[str, str]] = {
    "glioma": "Masa intraaxial con realce heterogéneo · corte sagital",
    "meningioma": "Lesión extraaxial de base dural bien delimitada",
    "pituitary": "Lesión selar con posible extensión supraselar",
    "healthy": "Sin hallazgos compatibles con tumor · parénquima normal",
}

ETIQUETA_METODO: Final[str] = "Oclusión 32 px · paso 16 px"
CELDAS_POR_LADO: Final[int] = 14

FOCO_LESION: Final[dict[str, dict[str, float] | None]] = {
    "glioma": {"cx": 62, "cy": 38, "r": 12},
    "meningioma": {"cx": 24, "cy": 50, "r": 9},
    "pituitary": {"cx": 50, "cy": 68, "r": 7},
    "healthy": None,
}

CRANEO: Final[dict[str, float]] = {"cx": 50, "cy": 50, "rx": 42, "ry": 46}
PARENQUIMA: Final[dict[str, float]] = {"cx": 50, "cy": 52}

_MASCARA_32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    """Equivalente de `Math.imul` manteniendo la aritmética en 32 bits."""
    return (a * b) & _MASCARA_32


def _semilla(*partes: str) -> int:
    """FNV-1a de 32 bits, idéntico al del frontend."""
    hash_ = 0x811C9DC5
    for caracter in "|".join(partes):
        hash_ = (hash_ ^ ord(caracter)) & _MASCARA_32
        hash_ = _imul(hash_, 0x01000193)
    return hash_


def _mulberry32(semilla: int) -> Callable[[], float]:
    estado = {"valor": semilla & _MASCARA_32}

    def siguiente() -> float:
        estado["valor"] = (estado["valor"] + 0x6D2B79F5) & _MASCARA_32
        actual = estado["valor"]
        valor = _imul(actual ^ (actual >> 15), 1 | actual)
        valor = ((valor + _imul(valor ^ (valor >> 7), 61 | valor)) & _MASCARA_32) ^ valor
        valor &= _MASCARA_32
        return ((valor ^ (valor >> 14)) & _MASCARA_32) / 4294967296

    return siguiente


def _gaussiana(distancia: float, sigma: float) -> float:
    return math.exp(-(distancia * distancia) / (2 * sigma * sigma))


def _dentro_del_craneo(x: float, y: float) -> bool:
    dx = (x - CRANEO["cx"]) / CRANEO["rx"]
    dy = (y - CRANEO["cy"]) / CRANEO["ry"]
    return dx * dx + dy * dy <= 1


def _numero(valor: float) -> str:
    """Formatea como lo haría JavaScript al interpolar un número en texto."""
    if valor == int(valor):
        return str(int(valor))
    return repr(valor)


def _construir_celdas(clase: str, semilla: int) -> list[float]:
    aleatorio = _mulberry32(semilla)
    foco = FOCO_LESION[clase]
    paso = 100 / CELDAS_POR_LADO

    angulo_eco = aleatorio() * math.pi * 2
    distancia_eco = 14 + aleatorio() * 8
    centro_eco = (
        {
            "cx": foco["cx"] + math.cos(angulo_eco) * distancia_eco,
            "cy": foco["cy"] + math.sin(angulo_eco) * distancia_eco,
        }
        if foco
        else PARENQUIMA
    )

    celdas: list[float] = []
    for fila in range(CELDAS_POR_LADO):
        for columna in range(CELDAS_POR_LADO):
            x = (columna + 0.5) * paso
            y = (fila + 0.5) * paso

            if not _dentro_del_craneo(x, y):
                celdas.append(0)
                continue

            intensidad = 0.05 + aleatorio() * 0.12
            if foco:
                hasta_foco = math.hypot(x - foco["cx"], y - foco["cy"])
                hasta_eco = math.hypot(x - centro_eco["cx"], y - centro_eco["cy"])
                intensidad += _gaussiana(hasta_foco, foco["r"] * 1.15)
                intensidad += 0.32 * _gaussiana(hasta_eco, foco["r"] * 1.6)
            else:
                hasta_centro = math.hypot(x - PARENQUIMA["cx"], y - PARENQUIMA["cy"])
                intensidad += 0.55 * _gaussiana(hasta_centro, 26)
            celdas.append(intensidad)

    pico = max(celdas)
    if pico <= 0:
        return celdas
    return [math.floor((valor / pico) * 1000 + 0.5) / 1000 for valor in celdas]


def _mapa_como_data_uri(celdas: list[float]) -> str:
    paso = 100 / CELDAS_POR_LADO
    rectangulos: list[str] = []

    for indice, intensidad in enumerate(celdas):
        if intensidad < 0.04:
            continue
        columna = indice % CELDAS_POR_LADO
        fila = indice // CELDAS_POR_LADO
        x = math.floor(columna * paso * 100 + 0.5) / 100
        y = math.floor(fila * paso * 100 + 0.5) / 100
        lado = math.floor(paso * 1.04 * 100 + 0.5) / 100
        rectangulos.append(
            f'<rect x="{_numero(x)}" y="{_numero(y)}" width="{_numero(lado)}" '
            f'height="{_numero(lado)}" fill="#fff" fill-opacity="{_numero(intensidad)}"/>'
        )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="224" height="224">'
        '<defs><filter id="soften" x="-25%" y="-25%" width="150%" height="150%">'
        '<feGaussianBlur stdDeviation="2.4"/></filter></defs>'
        f'<g filter="url(#soften)">{"".join(rectangulos)}</g></svg>'
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="-_.!~*'()")


def generar_explicacion(clase: str, codigo_pais: str) -> dict[str, str]:
    """Explicación determinista: misma clase y país, mismo mapa."""
    celdas = _construir_celdas(clase, _semilla(clase, codigo_pais))
    return {
        "method": "occlusion",
        "method_label": ETIQUETA_METODO,
        "influence_map_data_uri": _mapa_como_data_uri(celdas),
    }


def _repartir_confianza(predicha: str) -> dict[str, float]:
    principal = 90 + _random.random() * 8
    restante = 100 - principal
    otras = [clase for clase in CLASES_TUMOR if clase != predicha]
    pesos = [_random.random() for _ in otras]
    suma = sum(pesos)

    confianzas = {predicha: math.floor(principal * 10 + 0.5) / 10}
    for clase, peso in zip(otras, pesos, strict=True):
        confianzas[clase] = math.floor(restante * (peso / suma) * 10 + 0.5) / 10
    return confianzas


def clasificar(
    codigo_pais: str,
    *,
    pista: str | None = None,
    explicar: bool = True,
    version_modelo: str,
    etiqueta_preproceso: str,
) -> dict[str, Any]:
    clase = pista if pista in CLASES_TUMOR else _random.choice(CLASES_TUMOR)
    return {
        "predicted_class": clase,
        "confidence_by_class": _repartir_confianza(clase),
        "description": DESCRIPCIONES[clase],
        "model_version": version_modelo,
        "preprocess": etiqueta_preproceso,
        "country_code": codigo_pais,
        "explanation": generar_explicacion(clase, codigo_pais) if explicar else None,
    }
