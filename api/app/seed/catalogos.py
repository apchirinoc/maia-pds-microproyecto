"""Catálogos: países y clases de tumor.

Mientras `DATA_SOURCE=seed` estos datos viven en memoria. Al pasar a
`postgres` los sustituyen las tablas `countries` y `tumor_classes` sin que
cambie ni el contrato ni los routers.
"""

from __future__ import annotations

from typing import Final

CLASES_TUMOR: Final[tuple[str, ...]] = ("glioma", "meningioma", "pituitary", "healthy")

PAISES: Final[list[dict[str, object]]] = [
    {"code": "AR", "name": "Argentina", "latitude": -34.6, "longitude": -58.4},
    {"code": "AU", "name": "Australia", "latitude": -25.3, "longitude": 133.8},
    {"code": "BR", "name": "Brazil", "latitude": -15.8, "longitude": -47.9},
    {"code": "CA", "name": "Canada", "latitude": 56.1, "longitude": -106.3},
    {"code": "CL", "name": "Chile", "latitude": -35.7, "longitude": -71.5},
    {"code": "CN", "name": "China", "latitude": 35.9, "longitude": 104.2},
    {"code": "CO", "name": "Colombia", "latitude": 4.6, "longitude": -74.1},
    {"code": "EC", "name": "Ecuador", "latitude": -1.8, "longitude": -78.2},
    {"code": "EG", "name": "Egypt", "latitude": 26.8, "longitude": 30.8},
    {"code": "FR", "name": "France", "latitude": 46.2, "longitude": 2.2},
    {"code": "DE", "name": "Germany", "latitude": 51.2, "longitude": 10.5},
    {"code": "IN", "name": "India", "latitude": 20.6, "longitude": 79.0},
    {"code": "ID", "name": "Indonesia", "latitude": -0.8, "longitude": 113.9},
    {"code": "IT", "name": "Italy", "latitude": 41.9, "longitude": 12.6},
    {"code": "JP", "name": "Japan", "latitude": 36.2, "longitude": 138.3},
    {"code": "MX", "name": "Mexico", "latitude": 23.6, "longitude": -102.6},
    {"code": "NL", "name": "Netherlands", "latitude": 52.1, "longitude": 5.3},
    {"code": "NG", "name": "Nigeria", "latitude": 9.1, "longitude": 8.7},
    {"code": "PE", "name": "Peru", "latitude": -9.2, "longitude": -75.0},
    {"code": "PL", "name": "Poland", "latitude": 51.9, "longitude": 19.1},
    {"code": "PT", "name": "Portugal", "latitude": 39.4, "longitude": -8.2},
    {"code": "SA", "name": "Saudi Arabia", "latitude": 23.9, "longitude": 45.1},
    {"code": "ZA", "name": "South Africa", "latitude": -30.6, "longitude": 22.9},
    {"code": "ES", "name": "Spain", "latitude": 40.5, "longitude": -3.7},
    {"code": "SE", "name": "Sweden", "latitude": 60.1, "longitude": 18.6},
    {"code": "TR", "name": "Turkey", "latitude": 38.9, "longitude": 35.2},
    {"code": "GB", "name": "United Kingdom", "latitude": 55.4, "longitude": -3.4},
    {"code": "US", "name": "United States of America", "latitude": 39.8, "longitude": -98.6},
]

CARGAS_POR_PAIS: Final[list[dict[str, object]]] = [
    {"country_code": "US", "country_name": "United States of America", "uploads": 4826},
    {"country_code": "IN", "country_name": "India", "uploads": 3260},
    {"country_code": "CN", "country_name": "China", "uploads": 2480},
    {"country_code": "BR", "country_name": "Brazil", "uploads": 620},
    {"country_code": "MX", "country_name": "Mexico", "uploads": 480},
    {"country_code": "GB", "country_name": "United Kingdom", "uploads": 410},
    {"country_code": "DE", "country_name": "Germany", "uploads": 350},
    {"country_code": "FR", "country_name": "France", "uploads": 300},
    {"country_code": "CA", "country_name": "Canada", "uploads": 280},
    {"country_code": "ES", "country_name": "Spain", "uploads": 220},
    {"country_code": "CO", "country_name": "Colombia", "uploads": 180},
    {"country_code": "IT", "country_name": "Italy", "uploads": 160},
    {"country_code": "JP", "country_name": "Japan", "uploads": 150},
    {"country_code": "AU", "country_name": "Australia", "uploads": 140},
    {"country_code": "AR", "country_name": "Argentina", "uploads": 120},
    {"country_code": "TR", "country_name": "Turkey", "uploads": 110},
    {"country_code": "NG", "country_name": "Nigeria", "uploads": 100},
    {"country_code": "ZA", "country_name": "South Africa", "uploads": 90},
    {"country_code": "EG", "country_name": "Egypt", "uploads": 85},
    {"country_code": "ID", "country_name": "Indonesia", "uploads": 80},
    {"country_code": "NL", "country_name": "Netherlands", "uploads": 75},
    {"country_code": "PL", "country_name": "Poland", "uploads": 70},
    {"country_code": "SE", "country_name": "Sweden", "uploads": 60},
    {"country_code": "PT", "country_name": "Portugal", "uploads": 55},
    {"country_code": "SA", "country_name": "Saudi Arabia", "uploads": 50},
    {"country_code": "PE", "country_name": "Peru", "uploads": 45},
    {"country_code": "CL", "country_name": "Chile", "uploads": 40},
    {"country_code": "EC", "country_name": "Ecuador", "uploads": 21},
]
