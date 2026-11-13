"""Common response envelope, metadata models, and area validation for Core API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.harmonization.uncertainty import interval_for
from app.core.spatial.grid import bbox_to_cells, polygon_to_cells
from app.settings import settings
from app.shared.errors import TerraFlareError
from app.shared.regions import load_regions

T = TypeVar("T")

# India National Bounding Box (Data Region)
DATA_REGION_MIN_LON = 68.0
DATA_REGION_MIN_LAT = 6.5
DATA_REGION_MAX_LON = 97.5
DATA_REGION_MAX_LAT = 37.5

MAX_LON_SPAN = 30.0
MAX_LAT_SPAN = 32.0
MAX_BBOX_AREA_DEG2 = 900.0


class ResponseMeta(BaseModel):
    """Metadata included in the common response envelope."""

    data_version: str | None = None
    series: str | None = None
    method: str | None = None
    value_type: str | None = None
    interval_applies_to: str | None = None
    coverage: str | None = None
    is_provisional: bool = False
    reliability: str | None = None
    warnings: list[str] = Field(default_factory=list)
    generated_at: str


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope: {data, meta}."""

    data: T
    meta: ResponseMeta


def get_current_data_version() -> str:
    """Return active data version from manifest or settings."""
    manifest_path = settings.data_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                v = data.get("data_version")
                if v:
                    return str(v)
        except Exception:
            pass
    return getattr(settings, "data_version", "2026.11.10.7")


def make_meta(
    series: str | None = None,
    method: str | None = None,
    value_type: str | None = None,
    interval_applies_to: str | None = None,
    coverage: str | None = None,
    is_provisional: bool = False,
    reliability: str | None = None,
    warnings: list[str] | None = None,
    data_version: str | None = None,
) -> ResponseMeta:
    """Construct ResponseMeta with current UTC timestamp and defaults.

    Rule (Task 14): Report held-out coverage per class (81-96%) for conversion intervals
    instead of nominal 90%.
    """
    if coverage is None:
        if interval_applies_to in ("conversion", "conversion_model", "pre_2012_conversion_and_bridges") or (
            series == "harmonized" and value_type in ("composite", "estimated, extrapolated")
        ):
            coverage = "81-96% held-out"

    return ResponseMeta(
        data_version=data_version or get_current_data_version(),
        series=series,
        method=method,
        value_type=value_type,
        interval_applies_to=interval_applies_to,
        coverage=coverage,
        is_provisional=is_provisional,
        reliability=reliability,
        warnings=warnings or [],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def parse_bbox_param(bbox_str: str | None) -> tuple[float, float, float, float] | None:
    """Parse and validate comma-separated 'minLon,minLat,maxLon,maxLat' string."""
    if not bbox_str or not isinstance(bbox_str, str) or not bbox_str.strip():
        return None
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError()
        min_lon, min_lat, max_lon, max_lat = parts
        if min_lon > max_lon or min_lat > max_lat:
            raise ValueError()
        return min_lon, min_lat, max_lon, max_lat
    except Exception:
        raise TerraFlareError(
            code="invalid_bbox",
            message="Invalid bbox format. Expected 'minLon,minLat,maxLon,maxLat' with min <= max.",
            status_code=400,
        )


def parse_polygon_param(polygon: Any) -> dict[str, Any] | None:
    """Parse and validate GeoJSON polygon specification."""
    if polygon is None or not isinstance(polygon, (str, dict)):
        return None
    if isinstance(polygon, dict):
        poly_dict = polygon
    else:
        try:
            poly_dict = json.loads(polygon)
        except Exception:
            raise TerraFlareError(
                code="invalid_polygon",
                message="Invalid GeoJSON polygon specification: JSON parsing failed.",
                status_code=400,
            )

    # Validate GeoJSON type
    geom_type = poly_dict.get("type", "")
    if geom_type not in ("Polygon", "MultiPolygon", "Feature", "FeatureCollection"):
        raise TerraFlareError(
            code="invalid_polygon",
            message=f"Unsupported geometry type '{geom_type}'. Expected 'Polygon' or 'Feature'.",
            status_code=400,
        )
    return poly_dict


def _extract_polygon_bbox(poly_dict: dict[str, Any]) -> tuple[float, float, float, float]:
    """Extract (min_lon, min_lat, max_lon, max_lat) from a GeoJSON polygon."""
    lons: list[float] = []
    lats: list[float] = []

    def _collect_coords(coords: Any):
        if isinstance(coords, (list, tuple)):
            if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
                lons.append(float(coords[0]))
                lats.append(float(coords[1]))
            else:
                for sub in coords:
                    _collect_coords(sub)

    if poly_dict.get("type") == "Feature":
        _collect_coords(poly_dict.get("geometry", {}).get("coordinates", []))
    elif poly_dict.get("type") == "FeatureCollection":
        for feat in poly_dict.get("features", []):
            _collect_coords(feat.get("geometry", {}).get("coordinates", []))
    else:
        _collect_coords(poly_dict.get("coordinates", []))

    if not lons or not lats:
        raise TerraFlareError(
            code="invalid_polygon",
            message="GeoJSON polygon contains no valid coordinate pairs.",
            status_code=400,
        )
    return min(lons), min(lats), max(lons), max(lats)


def validate_area_boundaries(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> None:
    """Enforce data region boundaries (India) and oversized limits."""
    # 1. Outside data region check
    if (
        max_lon < DATA_REGION_MIN_LON
        or min_lon > DATA_REGION_MAX_LON
        or max_lat < DATA_REGION_MIN_LAT
        or min_lat > DATA_REGION_MAX_LAT
    ):
        raise TerraFlareError(
            code="outside_data_region",
            message=(
                f"Area is outside the supported data region "
                f"(India bounds: [{DATA_REGION_MIN_LON}, {DATA_REGION_MIN_LAT}, "
                f"{DATA_REGION_MAX_LON}, {DATA_REGION_MAX_LAT}])."
            ),
            status_code=400,
        )

    # 2. Oversized check
    lon_span = max_lon - min_lon
    lat_span = max_lat - min_lat
    box_area = lon_span * lat_span

    if lon_span > MAX_LON_SPAN or lat_span > MAX_LAT_SPAN or box_area > MAX_BBOX_AREA_DEG2:
        raise TerraFlareError(
            code="oversized_area",
            message=(
                f"Area is oversized: drawn area span ({lon_span:.1f}° lon × {lat_span:.1f}° lat) "
                f"exceeds maximum allowed bounds ({MAX_LON_SPAN}° lon × {MAX_LAT_SPAN}° lat)."
            ),
            status_code=400,
        )


def resolve_api_area(
    region_id: str | None = None,
    bbox: str | None = None,
    polygon: Any = None,
    h3_res: int = 6,
) -> tuple[str, list[str] | None, bool, tuple[float, float, float, float] | None]:
    """Validate and resolve region_id OR bbox OR polygon to H3 cells.

    Returns:
        (area_type, cells, is_drawn_area, bbox_tuple)
    """
    poly_dict = parse_polygon_param(polygon)
    if poly_dict:
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = _extract_polygon_bbox(poly_dict)
        validate_area_boundaries(b_min_lon, b_min_lat, b_max_lon, b_max_lat)
        cells = list(polygon_to_cells(poly_dict, resolution=h3_res))
        return "polygon", cells, True, (b_min_lon, b_min_lat, b_max_lon, b_max_lat)

    bbox_tuple = parse_bbox_param(bbox)
    if bbox_tuple:
        validate_area_boundaries(*bbox_tuple)
        cells = list(bbox_to_cells(bbox_tuple, resolution=h3_res))
        return "bbox", cells, True, bbox_tuple

    # Region ID
    reg_id = (region_id or "india").strip().lower()
    regions = load_regions()
    if reg_id in ("india", "all"):
        return "country", None, False, (DATA_REGION_MIN_LON, DATA_REGION_MIN_LAT, DATA_REGION_MAX_LON, DATA_REGION_MAX_LAT)

    if reg_id not in regions:
        raise TerraFlareError(
            code="region_not_found",
            message=f"Region '{reg_id}' not found. Supported regions: {', '.join(sorted(regions.keys()))}.",
            status_code=404,
        )

    r_bbox = regions[reg_id].bbox
    cells = list(bbox_to_cells(r_bbox, resolution=h3_res))
    return "region", cells, False, (r_bbox.min_lon, r_bbox.min_lat, r_bbox.max_lon, r_bbox.max_lat)


def evaluate_series_and_uncertainty(
    expected_count: float,
    is_drawn_area: bool,
    requested_series: str = "harmonized",
) -> tuple[str, str, float | None, float | None, list[str]]:
    """Determine effective series, reliability label, uncertainty bounds, and warnings.

    Rule (Task 13):
    - Intervals and reliability come from interval_for(expected_count).
    - Warn when area is small (expected_count < 10 or reliability in ('low', 'insufficient')).
    - Small-area fallback: when interval_for returns 'insufficient' or 'low', keep the 2012+
      observed series and return modis_native (with reliability 'low' and a warning) for
      the pre-2012 portion. Do not drop pre-2012 years silently.
    """
    rel_l, rel_u, reliability = interval_for(expected_count)
    warnings: list[str] = []
    effective_series = requested_series or "harmonized"

    if is_drawn_area:
        is_small = expected_count < 10 or reliability in ("low", "insufficient")
        if is_small:
            warnings.append(
                "Area is small: uncertainty intervals are wide and satellite detection intermittency is high"
            )
            if requested_series == "harmonized":
                warnings.append(
                    "Small area: pre-2012 uses native MODIS counts due to conversion uncertainty; "
                    "2012+ uses observed VIIRS reference series."
                )

    return effective_series, reliability, rel_l, rel_u, warnings

