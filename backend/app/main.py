"""TerraFlare FastAPI application entry point.

CORS is configured from settings.cors_origins (no wildcard, no credentials).
The API is split into:
  /api/v1/          – core routes (health, regions, hotspots, history, …)
  /api/v1/advanced/ – advanced analytics (season-shift, fire-memory, …)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.core_router import core_router
from app.api.router import api_router as advanced_router
from app.settings import settings
from app.shared.errors import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DuckDB views are registered relative to TERRAFLARE_DATA_DIR at startup
    try:
        from app.core.storage.duckdb_repo import DuckDBRepository
        repo = DuckDBRepository()
        _ = repo.con
    except Exception:
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS: explicit origin list only – no wildcard, no allow_credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Core routes: /api/v1/health, /api/v1/regions, etc.
app.include_router(core_router, prefix=settings.api_prefix)

# Advanced analytics routes: /api/v1/advanced/…
app.include_router(advanced_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs"}
