"""Entorno de ejecución de Alembic.

Dos decisiones que conviene tener presentes al leer este archivo:

1. **Driver síncrono.** La aplicación habla con Postgres por `asyncpg`, pero
   Alembic ejecuta las migraciones de forma síncrona. En vez de montar el
   envoltorio asíncrono, se traduce la URL de `DATABASE_URL` a `psycopg`
   (síncrono). Es la misma base, el mismo esquema y una pieza menos de
   complejidad en el arranque de las migraciones.

2. **`target_metadata` es None a propósito.** La línea base del esquema es el
   DDL de `model/scripts/ddl/`, no los modelos ORM: `app/models/entidades.py`
   cubre 15 de las 17 tablas (faltan `refresh_tokens` y
   `dataset_snapshot_items`) y no declara triggers, vistas ni funciones. Apuntar
   `--autogenerate` contra esos modelos propondría borrar lo que no conoce. Ver
   `alembic/README.md`.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# `alembic` se invoca normalmente desde `api/`, pero también desde otros
# directorios: se asegura que `app` sea importable para reutilizar su
# configuración en vez de duplicar la cadena de conexión aquí.
RAIZ_API = Path(__file__).resolve().parents[1]
if str(RAIZ_API) not in sys.path:
    sys.path.insert(0, str(RAIZ_API))

from app.core.config import get_settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ver el punto 2 del docstring: la evolución del esquema se escribe a mano.
target_metadata = None

DRIVER_SINCRONO = "postgresql+psycopg"


def url_sincrona() -> str:
    """URL de conexión con driver síncrono.

    Prioriza `ALEMBIC_DATABASE_URL` si está definida —útil para apuntar a una
    base distinta de la que sirve la aplicación— y en su defecto reescribe
    `DATABASE_URL` cambiando el driver asíncrono por uno síncrono.
    """
    explicita = os.getenv("ALEMBIC_DATABASE_URL")
    if explicita:
        return explicita

    url = get_settings().database_url
    if not url:
        raise RuntimeError(
            "No hay DATABASE_URL configurada. Alembic necesita una base real: "
            "defínela en api/.env o exporta ALEMBIC_DATABASE_URL."
        )

    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", f"{DRIVER_SINCRONO}://", 1)
    return url


def ejecutar_migraciones_sin_conexion() -> None:
    """Modo «offline»: emite el SQL sin conectarse a la base."""
    context.configure(
        url=url_sincrona(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def ejecutar_migraciones_con_conexion() -> None:
    """Modo «online»: abre una conexión y aplica las revisiones."""
    seccion = config.get_section(config.config_ini_section, {}) or {}
    seccion["sqlalchemy.url"] = url_sincrona()

    conectable = engine_from_config(
        seccion,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with conectable.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    ejecutar_migraciones_sin_conexion()
else:
    ejecutar_migraciones_con_conexion()
