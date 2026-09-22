"""Línea base v1 del esquema.

Revision ID: 0001_linea_base
Revises:
Create Date: 2026-09-05

Esta revisión **no crea nada**: representa el esquema que ya construyen los
scripts de `model/scripts/ddl/`, que son la línea base v1 acordada en la
sección 10.6 del plan.

Por qué está vacía en lugar de recrear las 17 tablas:

* El DDL declara triggers, vistas, índices únicos parciales y comentarios de
  columna que `--autogenerate` no sabe reproducir. Duplicarlos aquí crearía dos
  definiciones del mismo esquema que se desincronizarían a la primera
  divergencia.
* Los modelos ORM cubren 15 de las 17 tablas, así que una migración generada a
  partir de ellos propondría además **borrar** `refresh_tokens` y
  `dataset_snapshot_items`.

Una base nueva se levanta con `docker compose up` en `model/`, que aplica el
DDL, y después se marca con `alembic stamp head`. A partir de ahí toda
evolución del esquema entra por revisiones escritas a mano.
"""

from __future__ import annotations

revision = "0001_linea_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Sin operaciones: el esquema lo crea el DDL de `model/`."""


def downgrade() -> None:
    """No se revierte la línea base.

    Deshacerla significaría destruir el esquema completo, que es justo lo que
    `docker compose down -v` hace de forma explícita y consciente.
    """
    raise RuntimeError(
        "La línea base no se revierte. Para partir de cero: "
        "cd model && docker compose down -v && docker compose up -d"
    )
