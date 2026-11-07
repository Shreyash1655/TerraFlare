from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.dependencies import RepoDep

api_router = APIRouter(prefix="/advanced")


@api_router.get("/health", tags=["Health"])
def advanced_health(repo: RepoDep):
    return {"status": "ok", "data_mode": repo.mode, "data_version": repo.data_version,
            "is_synthetic": repo.is_synthetic, "features_enabled": list(settings.enabled_features)}


def _on(name: str) -> bool:
    return name in settings.enabled_features


if _on("season-shift"):
    from app.api.routes import season_shift
    api_router.include_router(season_shift.router, prefix="/season-shift")
if _on("fire-memory"):
    from app.api.routes import fire_memory
    api_router.include_router(fire_memory.router, prefix="/fire-memory")
if _on("anomaly"):
    from app.api.routes import anomalies
    api_router.include_router(anomalies.router, prefix="/anomalies")
if _on("events"):
    from app.api.routes import events
    api_router.include_router(events.router, prefix="/events")
if _on("exposure"):
    from app.api.routes import exposure
    api_router.include_router(exposure.router, prefix="/exposure")
if _on("quality"):
    from app.api.routes import quality
    api_router.include_router(quality.router, prefix="/quality")