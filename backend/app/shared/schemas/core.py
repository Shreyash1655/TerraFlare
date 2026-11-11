"""Core API schemas (health, capabilities, regions, hotspots, etc.)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema for GET /api/v1/health."""

    status: str
    service: str
    data_mode: str
    is_synthetic: bool
    data_version: str | None = None
    manifest_summary: dict[str, Any] | None = None


class CapabilitiesResponse(BaseModel):
    """Response schema for GET /api/v1/meta/capabilities."""

    sensors: list[str] = ["MODIS", "VIIRS"]
    h3_resolution: int = 6
    has_frp: bool = True
    has_confidence: bool = True
    has_day_night: bool = True
    has_platform: bool = True
    has_fire_type: bool = True
    data_version: str | None = None
    features_enabled: list[str] = []


