"""GET /api/v1/meta/capabilities – capability and version metadata wrapped in common envelope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.settings import settings
from app.shared.api_envelope import ApiResponse, ResponseMeta, make_meta
from app.shared.config_loader import get_harmonization_config

router = APIRouter(tags=["Meta"])


class CapabilitiesData(BaseModel):
    """Payload for /meta/capabilities."""

    service: str = "TerraFlare Core API"
    version: str = "1.0"
    supported_series: list[str] = ["harmonized", "viirs_native", "modis_native"]
    sensors: list[str] = ["MODIS", "VIIRS"]
    platforms: list[str] = ["Terra", "Aqua", "S-NPP", "NOAA-20", "NOAA-21"]
    h3_resolution: int = 6
    has_frp: bool = True
    has_confidence: bool = True
    has_day_night: bool = True
    has_platform: bool = True
    has_fire_type: bool = True
    features_enabled: list[str] = []


class CapabilitiesEnvelope(ApiResponse[CapabilitiesData]):
    """Standard envelope for /meta/capabilities."""

    pass


def _read_manifest(data_dir: Path) -> dict[str, Any] | None:
    manifest_path = data_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError, KeyError):
            return None
    return None


@router.get("/meta/capabilities", response_model=CapabilitiesEnvelope)
def get_capabilities() -> dict[str, Any]:
    """Return pipeline capabilities, sensors, and resolution wrapped in common envelope."""
    manifest = _read_manifest(settings.data_dir)
    default_res = int(get_harmonization_config().get("h3_resolution", 6))
    data_ver = manifest.get("data_version") if manifest else None

    if manifest:
        caps = manifest.get("capabilities", {})
        data = CapabilitiesData(
            service="TerraFlare Core API",
            version="1.0",
            supported_series=["harmonized", "viirs_native", "modis_native"],
            sensors=["MODIS", "VIIRS"],
            platforms=["Terra", "Aqua", "S-NPP", "NOAA-20", "NOAA-21"],
            h3_resolution=int(manifest.get("h3_resolution", default_res)),
            has_frp=bool(caps.get("has_frp", True)),
            has_confidence=bool(caps.get("has_confidence", True)),
            has_day_night=bool(caps.get("has_day_night", True)),
            has_platform=bool(caps.get("has_platform", True)),
            has_fire_type=bool(caps.get("has_fire_type", True)),
            features_enabled=list(settings.enabled_features),
        )
    else:
        data = CapabilitiesData(
            service="TerraFlare Core API",
            version="1.0",
            supported_series=["harmonized", "viirs_native", "modis_native"],
            sensors=["MODIS", "VIIRS"],
            platforms=["Terra", "Aqua", "S-NPP", "NOAA-20", "NOAA-21"],
            h3_resolution=default_res,
            has_frp=True,
            has_confidence=True,
            has_day_night=True,
            has_platform=True,
            has_fire_type=True,
            features_enabled=list(settings.enabled_features),
        )

    meta = make_meta(data_version=data_ver)
    return {"data": data, "meta": meta}
