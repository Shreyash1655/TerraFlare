"""H3 spatial grid assignment and geometry conversion using H3 v4."""

from __future__ import annotations

from typing import Any

import h3
import numpy as np
import pandas as pd

from app.shared.config_loader import get_harmonization_config


def get_default_resolution() -> int:
    """Read h3_resolution from harmonization.yaml, defaulting to 6."""
    return int(get_harmonization_config().get("h3_resolution", 6))


def assign_h3_cells(
    df: pd.DataFrame,
    resolution: int | None = None,
) -> pd.DataFrame:
    """Assigns H3 cell ids to lat/lon pairs using unique mapping for performance.

    Missing/invalid coordinates are mapped to None (object dtype).
    """
    out = df.copy()
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        out["h3_cell"] = None
        return out

    res = resolution if resolution is not None else get_default_resolution()

    # Mask valid coordinates
    valid_mask = out["lat"].notna() & out["lon"].notna()

    # Initialize column with None
    out["h3_cell"] = None

    if valid_mask.any():
        # Get unique valid pairs to minimize H3 calls
        unique_coords = out.loc[valid_mask, ["lat", "lon"]].drop_duplicates()
        coord_map = {}
        for row in unique_coords.itertuples(index=False):
            try:
                coord_map[(row.lat, row.lon)] = h3.latlng_to_cell(
                    float(row.lat), float(row.lon), res
                )
            except Exception:
                continue

        # Apply mapping back to valid rows
        keys = list(zip(out.loc[valid_mask, "lat"], out.loc[valid_mask, "lon"]))
        out.loc[valid_mask, "h3_cell"] = [coord_map.get(k) for k in keys]

    # Explicitly ensure invalid/NaN rows remain Python None (object dtype)
    out["h3_cell"] = out["h3_cell"].where(out["h3_cell"].notna(), None)

    return out


def bbox_to_cells(
    bbox: list[float] | tuple[float, float, float, float] | Any,
    resolution: int | None = None,
) -> set[str]:
    """Convert a bounding box [min_lon, min_lat, max_lon, max_lat] to a set of H3 cells.

    Uses H3 v4 LatLngPoly with vertices:
      (min_lat, min_lon), (min_lat, max_lon), (max_lat, max_lon), (max_lat, min_lon)
    """
    res = resolution if resolution is not None else get_default_resolution()

    if hasattr(bbox, "as_list"):
        min_lon, min_lat, max_lon, max_lat = bbox.as_list()
    elif hasattr(bbox, "min_lon"):
        min_lon, min_lat, max_lon, max_lat = bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat
    else:
        min_lon, min_lat, max_lon, max_lat = bbox

    # H3 v4 LatLngPoly takes lat, lng pairs
    poly = h3.LatLngPoly([
        (float(min_lat), float(min_lon)),
        (float(min_lat), float(max_lon)),
        (float(max_lat), float(max_lon)),
        (float(max_lat), float(min_lon)),
    ])
    return set(h3.polygon_to_cells(poly, res))


def polygon_to_cells(
    geojson_polygon: dict[str, Any] | Any,
    resolution: int | None = None,
) -> set[str]:
    """Convert a GeoJSON Polygon dictionary or H3 shape to a set of H3 cells using H3 v4."""
    res = resolution if resolution is not None else get_default_resolution()

    if isinstance(geojson_polygon, dict):
        shape = h3.geo_to_h3shape(geojson_polygon)
        return set(h3.polygon_to_cells(shape, res))
    elif isinstance(geojson_polygon, (h3.LatLngPoly, h3.LatLngMultiPoly)):
        return set(h3.polygon_to_cells(geojson_polygon, res))
    elif hasattr(geojson_polygon, "__geo_interface__"):
        shape = h3.geo_to_h3shape(geojson_polygon.__geo_interface__)
        return set(h3.polygon_to_cells(shape, res))
    else:
        raise ValueError(f"Unsupported geometry type: {type(geojson_polygon)}")

