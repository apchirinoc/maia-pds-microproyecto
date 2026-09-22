"""Agrega los routers de la versión 1 de la API."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, cargas, catalogos, clasificaciones, meta, modelos, panel

router = APIRouter(prefix="/api/v1")
router.include_router(meta.router)
router.include_router(auth.router)
router.include_router(catalogos.router)
router.include_router(panel.router)
router.include_router(modelos.router)
router.include_router(cargas.router)
router.include_router(clasificaciones.router)
