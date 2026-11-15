"""GET /api/v1/health – service liveness, data mode, and common envelope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.settings import settings
from app.shared.api_envelope import ApiResponse, ResponseMeta, make_meta

router = APIRouter(tags=["Health"])


class HealthData(BaseModel):
    """Payload for /health."""

    status: str
    service: str
    data_mode: str
    is_synthetic: bool
    manifest_summary: dict[str, Any] | None = None
    data_version: str | None = None


class HealthEnvelope(ApiResponse[HealthData]):
    """Standard envelope for /health."""

    pass


def _read_manifest_info() -> tuple[str | None, dict[str, Any] | None]:
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


@router.get("/health", response_model=HealthEnvelope)
def health() -> dict[str, Any]:
    """Return service liveness, data mode, and data version wrapped in common envelope."""
    version, summary = _read_manifest_info()
    data = HealthData(
        status="ok",
        service=settings.app_name,
        data_mode=settings.data_mode,
        is_synthetic=settings.data_mode == "fixture",
        manifest_summary=summary,
        data_version=version,
    )
    meta = make_meta(data_version=version)
    return {"data": data, "meta": meta}
