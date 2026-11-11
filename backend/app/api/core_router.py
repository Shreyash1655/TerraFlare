"""Core API router – aggregates all Member 1 core routes under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes_core.calendar import router as calendar_router
from app.api.routes_core.export import router as export_router
from app.api.routes_core.harmonization import router as harmonization_router
from app.api.routes_core.health import router as health_router
from app.api.routes_core.history import router as history_router
from app.api.routes_core.hotspots import router as hotspots_router
from app.api.routes_core.meta import router as meta_router
from app.api.routes_core.regions import router as regions_router

core_router = APIRouter()

core_router.include_router(health_router)
core_router.include_router(meta_router)
core_router.include_router(regions_router)
core_router.include_router(hotspots_router)
core_router.include_router(calendar_router)
core_router.include_router(history_router)
core_router.include_router(harmonization_router)
core_router.include_router(export_router)
