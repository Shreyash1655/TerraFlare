
"""Feature 5 - Fire Impact and Exposure: PROXIMITY of mapped assets to detected activity."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from app.core.config import settings
from app.utils.errors import TerraFlareError
from app.utils.response import iso, num


NOTE = "Proximity only. This is not damage, casualty or risk."

LIMITATIONS = [
    NOTE,
    "External layers have their own dates, resolution, completeness and licences; each is shown with its source and version.",
    "A layer that is not available is reported as unavailable, never as zero.",
    "Hotspot locations are detections rounded to ~1 km; footprints are not burned area.",
]


def _validate_buffer(buffer_km):
    """Validate the requested proximity buffer."""

    if not np.isfinite(buffer_km) or buffer_km <= 0:
        raise TerraFlareError(
            "invalid_buffer",
            "buffer_km must be a finite value greater than zero.",
            400,
        )


def _clean_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove records with invalid or missing geographic coordinates."""

    required = {"lat", "lon"}

    missing = required - set(df.columns)

    if missing:
        return pd.DataFrame(
            columns=list(df.columns)
        )

    result = df.copy()

    result["lat"] = pd.to_numeric(
        result["lat"],
        errors="coerce",
    )

    result["lon"] = pd.to_numeric(
        result["lon"],
        errors="coerce",
    )

    result = result.dropna(
        subset=["lat", "lon"]
    )

    result = result[
        result["lat"].between(-90, 90)
        & result["lon"].between(-180, 180)
    ]

    result = result[
        np.isfinite(result["lat"])
        & np.isfinite(result["lon"])
    ]

    return result


def _project(lat, lon, lat0, lon0):
    """Convert geographic coordinates into approximate local kilometres."""

    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)

    x = (
        (lon - lon0)
        * 111.32
        * np.cos(np.radians(lat0))
    )

    y = (
        (lat - lat0)
        * 110.574
    )

    return np.column_stack(
        [x, y]
    )


def _empty_layer(layer_id):
    """Standard response for a layer that is unavailable."""

    return {
        "layer_id": layer_id,
        "available": False,
    }


def compute_exposure(
    repo,
    region_id,
    start,
    end,
    buffer_km,
    layer_ids,
) -> dict:

    _validate_buffer(buffer_km)

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    if start > end:
        raise TerraFlareError(
            "invalid_date_range",
            "Start date must not be after end date.",
            400,
        )

    observations = repo.get_observations(
        region_id,
        start,
        end,
    )

    if observations is None:
        observations = pd.DataFrame()

    if observations.empty:
        pts = pd.DataFrame(
            columns=["lat", "lon"]
        )
    else:
        pts = _clean_coordinates(
            observations
        )

        # Round coordinates to approximately 1 km
        # to reduce repeated hotspot locations.
        pts = (
            pts[["lat", "lon"]]
            .round(2)
            .drop_duplicates()
            .reset_index(drop=True)
        )

    if len(pts) > settings.exposure_max_points:
        raise TerraFlareError(
            "too_many_locations",
            "Too many hotspot locations; narrow the dates or region.",
            422,
        )

    available = repo.get_layers() or {}

    requested = (
        list(layer_ids)
        if layer_ids is not None
        else list(available)
    )

    output = {
        "period": {
            "start": iso(start),
            "end": iso(end),
        },
        "buffer_km": buffer_km,
        "n_hotspot_locations": int(len(pts)),
        "layers": [],
        "note": NOTE,
        "notes": [],
    }

    # No valid hotspot locations.
    if pts.empty:

        output["notes"].append(
            "No valid hotspot locations were recorded in this period."
        )

        for layer_id in requested:
            if layer_id not in available:
                output["layers"].append(
                    _empty_layer(layer_id)
                )

        return output

    # -------------------------------------------------
    # Build spatial index of hotspot locations.
    # -------------------------------------------------

    lat0 = float(
        pts["lat"].mean()
    )

    lon0 = float(
        pts["lon"].mean()
    )

    hotspot_coordinates = _project(
        pts["lat"],
        pts["lon"],
        lat0,
        lon0,
    )

    tree = cKDTree(
        hotspot_coordinates
    )

    # -------------------------------------------------
    # Evaluate each requested geographic layer.
    # -------------------------------------------------

    for layer_id in requested:

        if layer_id not in available:

            output["layers"].append(
                _empty_layer(layer_id)
            )

            continue

        layer = available[layer_id]

        layer_df = layer.get("df")

        if not isinstance(layer_df, pd.DataFrame):

            output["layers"].append(
                _empty_layer(layer_id)
            )

            continue

        if layer_df.empty:

            output["layers"].append(
                {
                    "layer_id": layer_id,
                    "source": layer.get("source"),
                    "version": layer.get("version"),
                    "available": True,
                    "count": 0,
                    "sum_value": None,
                    "is_synthetic": bool(
                        layer.get("is_synthetic", False)
                    ),
                }
            )

            continue

        clean_layer = _clean_coordinates(
            layer_df
        )

        if clean_layer.empty:

            output["layers"].append(
                {
                    "layer_id": layer_id,
                    "source": layer.get("source"),
                    "version": layer.get("version"),
                    "available": True,
                    "count": 0,
                    "sum_value": None,
                    "is_synthetic": bool(
                        layer.get("is_synthetic", False)
                    ),
                }
            )

            continue

        # Convert asset coordinates into the same local
        # coordinate system as the hotspot locations.
        asset_coordinates = _project(
            clean_layer["lat"],
            clean_layer["lon"],
            lat0,
            lon0,
        )

        # Distance from each asset to its nearest hotspot.
        distances, _ = tree.query(
            asset_coordinates,
            k=1,
            distance_upper_bound=float(buffer_km),
        )

        exposed = np.isfinite(
            distances
        )

        exposed_count = int(
            exposed.sum()
        )

        # Sum values only for assets within the buffer.
        sum_value = None

        if "value" in clean_layer.columns:

            values = pd.to_numeric(
                clean_layer["value"],
                errors="coerce",
            )

            valid_values = values[
                exposed
            ]

            if valid_values.notna().any():

                sum_value = num(
                    valid_values.sum()
                )

        output["layers"].append(
            {
                "layer_id": layer_id,
                "source": layer.get("source"),
                "version": layer.get("version"),
                "available": True,
                "count": exposed_count,
                "sum_value": sum_value,
                "is_synthetic": bool(
                    layer.get("is_synthetic", False)
                ),
            }
        )

    if not available:

        output["notes"].append(
            "No external layers installed; place layer parquet files "
            "in data/processed/layers/."
        )

    elif any(
        layer_id not in available
        for layer_id in requested
    ):

        output["notes"].append(
            "Some requested geographic layers are unavailable."
        )

    output["notes"].append(
        "Counts represent mapped assets within the specified distance "
        "of at least one hotspot location."
    )

    return output
