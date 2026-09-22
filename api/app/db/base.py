"""Base declarativa de SQLAlchemy."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Raíz de todos los modelos ORM.

    El esquema canónico vive en `model/scripts/ddl/`. Estas clases lo espejan
    para poder consultarlo con tipos; la evolución del esquema entra por
    Alembic, no modificando estas clases a mano (sección 10.6 del plan).
    """
