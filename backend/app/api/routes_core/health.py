"""GET /api/v1/health – service liveness and data mode."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.settings import settings
from app.shared.schemas.core import HealthResponse

router = APIRouter(tags=["Health"])


def _read_manifest_info() -> tuple[str | None, dict | None]:
    """Return data_version and summary from data/manifest.json, or None."""
    manifest = settings.data_dir / "manifest.json"
    if manifest.exists():
        try:
            with manifest.open(encoding="utf-8") as fh:
                data = json.load(fh)
                version = data.get("data_version")
                summary = {
                    "data_version": str(version) if version else None,
                    "h3_resolution": data.get("h3_resolution"),
                    "row_counts": data.get("row_counts"),
                    "date_range": data.get("date_range"),
                    "git_commit": data.get("git_commit"),
                }
                return (str(version) if version else None, summary)
        except (OSError, ValueError, KeyError):
            return None, None
    return None, None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service liveness, data mode, and data version."""
    version, summary = _read_manifest_info()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        data_mode=settings.data_mode,
        is_synthetic=settings.data_mode == "fixture",
        data_version=version,
        manifest_summary=summary,
    )

