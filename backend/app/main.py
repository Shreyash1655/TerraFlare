
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.core import router as core_router
from app.api.routes.hotspots import router as hotspots_router
from app.api.routes_core.harmonization import (
    router as harmonization_router,
)
from app.core.config import settings
from app.utils.errors import register_error_handlers

app = FastAPI(
    title=settings.app_name,
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Existing advanced intelligence and FIRMS routes
app.include_router(api_router, prefix="/api/v1")

# Existing core routes
app.include_router(core_router, prefix="/api/v1")
app.include_router(hotspots_router, prefix="/api/v1")

# New harmonization routes
app.include_router(harmonization_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
    }
