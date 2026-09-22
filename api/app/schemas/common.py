"""Base común de los esquemas expuestos por la API.

El frontend está escrito en TypeScript con propiedades en `camelCase`. En vez de
traducir en el cliente, la API serializa directamente en `camelCase` mediante un
generador de alias, y el código Python conserva `snake_case`. Así el contrato de
OpenAPI encaja con los tipos que el frontend ya tiene, sin adaptadores.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class EsquemaBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ResultadoPaginado(EsquemaBase, Generic[T]):
    """Envolvente única de paginación, idéntica a `PaginatedResult<T>` del frontend."""

    items: list[T]
    total: int
    page: int
    page_size: int


class ProblemDetail(EsquemaBase):
    """Error normalizado según RFC 7807."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
