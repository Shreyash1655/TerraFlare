"""GET /api/v1/meta – capability and version metadata wired to manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.settings import settings
from app.shared.config_loader import get_harmonization_config
from app.shared.schemas.core import CapabilitiesResponse

router = APIRouter(tags=["Meta"])


def _read_manifest(data_dir: Path) -> dict[str, Any] | None:
    """Read manifest.json from data_dir if it exists."""
    manifest_path = data_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError, KeyError):
            return None
    return None


@router.get("/meta/capabilities", response_model=CapabilitiesResponse)
def get_capabilities() -> CapabilitiesResponse:
    """Return pipeline capabilities, sensors, and resolution wired to data/manifest.json."""
    manifest = _read_manifest(settings.data_dir)
    default_res = int(get_harmonization_config().get("h3_resolution", 6))

    if manifest:
        caps = manifest.get("capabilities", {})
        return CapabilitiesResponse(
            sensors=["MODIS", "VIIRS"],
            h3_resolution=int(manifest.get("h3_resolution", default_res)),
            has_frp=bool(caps.get("has_frp", True)),
            has_confidence=bool(caps.get("has_confidence", True)),
            has_day_night=bool(caps.get("has_day_night", True)),
            has_platform=bool(caps.get("has_platform", True)),
            has_fire_type=bool(caps.get("has_fire_type", True)),
            data_version=manifest.get("data_version"),
            features_enabled=list(settings.enabled_features),
        )

    return CapabilitiesResponse(
        sensors=["MODIS", "VIIRS"],
        h3_resolution=default_res,
        has_frp=True,
        has_confidence=True,
        has_day_night=True,
        has_platform=True,
        has_fire_type=True,
        data_version=None,
        features_enabled=list(settings.enabled_features),
    )
