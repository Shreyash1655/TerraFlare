"""Region registry with bounding-box helpers.

Regions are defined in config/regions.yaml.  This module loads them and
exposes lightweight helper functions used throughout the pipeline and API.

Bbox convention (follows GeoJSON):  [min_lon, min_lat, max_lon, max_lat]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.shared.config_loader import get_regions_config


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BBox:
    """Axis-aligned bounding box in WGS-84 degrees."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    # Convenience aliases
    @property
    def west(self) -> float:   return self.min_lon
    @property
    def south(self) -> float:  return self.min_lat
    @property
    def east(self) -> float:   return self.max_lon
    @property
    def north(self) -> float:  return self.max_lat

    def contains(self, lat: float, lon: float) -> bool:
        """Return True if the point (lat, lon) lies inside this bbox."""
        return (
            self.min_lat <= lat <= self.max_lat
            and self.min_lon <= lon <= self.max_lon
        )

    def as_list(self) -> list[float]:
        """Return [min_lon, min_lat, max_lon, max_lat]."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]

    def __str__(self) -> str:
        return (
            f"BBox(W={self.min_lon}, S={self.min_lat}, "
            f"E={self.max_lon}, N={self.max_lat})"
        )


@dataclass(frozen=True, slots=True)
class Region:
    """A named geographic region with a bounding box."""

    region_id: str
    name: str
    bbox: BBox
    description: str = ""

    def contains(self, lat: float, lon: float) -> bool:
        return self.bbox.contains(lat, lon)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _parse_region(raw: dict[str, Any]) -> Region:
    """Parse one region entry from the YAML dict."""
    bbox_raw = raw.get("bbox") or raw.get("bounds")
    if bbox_raw is None:
        # Support explicit keys as fallback
        bbox_raw = [
            raw["minLon"], raw["minLat"], raw["maxLon"], raw["maxLat"]
        ]
    min_lon, min_lat, max_lon, max_lat = bbox_raw
    return Region(
        region_id=raw["region_id"],
        name=raw.get("name", raw["region_id"]),
        bbox=BBox(
            min_lon=float(min_lon),
            min_lat=float(min_lat),
            max_lon=float(max_lon),
            max_lat=float(max_lat),
        ),
        description=raw.get("description", ""),
    )


def load_regions() -> dict[str, Region]:
    """Load all regions from config/regions.yaml.

    Returns a dict mapping region_id → Region.
    Returns {} if the config file does not exist.
    """
    raw = get_regions_config()
    return {rid: _parse_region(rdata) for rid, rdata in raw.items()}


def get_region(region_id: str) -> Region:
    """Return a Region by id, raising KeyError if not found."""
    regions = load_regions()
    if region_id not in regions:
        raise KeyError(
            f"Unknown region_id '{region_id}'. "
            f"Known regions: {list(regions.keys())}"
        )
    return regions[region_id]


def get_bbox(region_id: str) -> BBox:
    """Shortcut – return the BBox for a region_id."""
    return get_region(region_id).bbox


def list_region_ids() -> list[str]:
    """Return all configured region ids."""
    return list(load_regions().keys())


def point_in_region(lat: float, lon: float, region_id: str) -> bool:
    """Return True if (lat, lon) lies inside the named region's bbox."""
    return get_bbox(region_id).contains(lat, lon)
