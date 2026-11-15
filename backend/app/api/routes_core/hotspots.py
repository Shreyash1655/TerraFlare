"""Core API routes: /api/v1/hotspots and /api/v1/hotspots/cells wrapped in common envelope."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.shared.config_loader import get_harmonization_config
from app.core.harmonization.uncertainty import interval_for
from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.api_envelope import (
    ApiResponse,
    ResponseMeta,
    evaluate_series_and_uncertainty,
    make_meta,
    resolve_api_area,
)

router = APIRouter(tags=["hotspots"])
repo = DuckDBRepository()


def _clean_param(val: Any, default: Any = None) -> Any:
    if hasattr(val, "default"):
        return val.default if val.default is not ... else default
    return val if val is not None else default


@router.get("/hotspots")
def get_hotspots(
    region_id: str | None = Query(None, description="Region ID filter"),
    bbox: str | None = Query(None, description="Bounding box filter minLon,minLat,maxLon,maxLat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
    sensors: str | None = Query(None, description="Comma-separated sensor families (MODIS,VIIRS)"),
    confidence: str | None = Query(None, description="Minimum confidence class (low, nominal, high)"),
    limit: int = Query(5000, ge=1, le=10000, description="Maximum number of points to return"),
) -> dict[str, Any]:
    """Query hotspot point detections as GeoJSON FeatureCollection with common envelope."""
    region_id = _clean_param(region_id, None)
    bbox = _clean_param(bbox, None)
    polygon = _clean_param(polygon, None)
    start = _clean_param(start, None)
    end = _clean_param(end, None)
    sensors = _clean_param(sensors, None)
    confidence = _clean_param(confidence, None)
    limit = int(_clean_param(limit, 5000))

    area_type, cells, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon
    )

    clauses = ["is_valid = true"]
    params: list[Any] = []

    if cells is not None:
        if len(cells) == 0:
            features_data = {
                "type": "FeatureCollection",
                "truncated": False,
                "features": [],
                "reliability": "insufficient",
                "uncertainty_interval": None,
                "warning": "Area contains no valid grid cells.",
            }
            meta = make_meta(reliability="insufficient", warnings=["Area contains no valid grid cells."])
            return {"data": features_data, "meta": meta}
        clauses.append("h3_cell IN (SELECT unnest(?::VARCHAR[]))")
        params.append(cells)
    elif bbox_tuple:
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = bbox_tuple
        clauses.append(f"lon >= {b_min_lon} AND lon <= {b_max_lon} AND lat >= {b_min_lat} AND lat <= {b_max_lat}")

    if start:
        clauses.append(f"acq_date >= '{start}'")
    if end:
        clauses.append(f"acq_date <= '{end}'")

    if sensors:
        sensor_list = [s.strip().upper() for s in sensors.split(",") if s.strip()]
        if sensor_list:
            formatted = ", ".join(f"'{s}'" for s in sensor_list)
            clauses.append(f"UPPER(sensor_family) IN ({formatted})")

    if confidence:
        conf_lower = confidence.strip().lower()
        if conf_lower == "high":
            clauses.append("LOWER(confidence_class) = 'high'")
        elif conf_lower == "nominal":
            clauses.append("LOWER(confidence_class) IN ('nominal', 'high')")
        elif conf_lower == "low":
            clauses.append("LOWER(confidence_class) IN ('low', 'nominal', 'high')")

    where_sql = " AND ".join(clauses)
    query = f"""
        SELECT
            obs_id, sensor_family, platform, acq_datetime_utc, acq_date,
            confidence_class, frp_mw, processing_stream, lon, lat
        FROM obs_clean
        WHERE {where_sql}
        ORDER BY acq_date DESC, acq_datetime_utc DESC
        LIMIT {limit + 1}
    """

    try:
        df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
    except Exception:
        df = None

    features = []
    truncated = False
    is_any_prov = False

    if df is not None and not df.empty:
        total_count = len(df)
        if total_count > limit:
            truncated = True
            df = df.iloc[:limit]

        for _, row in df.iterrows():
            dt_utc = row["acq_datetime_utc"]
            dt_str = (
                dt_utc.isoformat()
                if hasattr(dt_utc, "isoformat") and dt_utc is not None
                else (str(dt_utc) if dt_utc is not None else None)
            )
            stream_val = str(row.get("processing_stream", "")).upper()
            is_prov = stream_val == "NRT"
            if is_prov:
                is_any_prov = True

            frp = row["frp_mw"]
            frp_val = float(frp) if frp is not None and str(frp) != "nan" else None

            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["lon"]), float(row["lat"])],
                },
                "properties": {
                    "obs_id": str(row["obs_id"]),
                    "sensor_family": str(row["sensor_family"]),
                    "platform": str(row["platform"]),
                    "acq_datetime_utc": dt_str,
                    "confidence_class": str(row["confidence_class"]) if row["confidence_class"] else "nominal",
                    "frp_mw": frp_val,
                    "is_provisional": is_prov,
                },
            }
            features.append(feat)

    expected = float(len(features))
    eff_series, reliability, rel_l, rel_u, warnings = evaluate_series_and_uncertainty(
        expected_count=expected,
        is_drawn_area=is_drawn_area,
        requested_series="harmonized",
    )

    if rel_l is not None and rel_u is not None:
        u_interval = [
            round(max(0.0, expected * (1.0 - rel_l)), 1),
            round(expected * (1.0 + rel_u), 1),
        ]
    else:
        u_interval = None

    features_data = {
        "type": "FeatureCollection",
        "truncated": truncated,
        "features": features,
        "reliability": reliability,
        "uncertainty_interval": u_interval,
        "warning": warnings[0] if warnings else None,
    }

    meta = make_meta(
        series=eff_series,
        method="stratified_ratio",
        is_provisional=is_any_prov,
        reliability=reliability,
        warnings=warnings,
    )
    return {"data": features_data, "meta": meta}


@router.get("/hotspots/cells")
def get_hotspot_cells(
    region_id: str | None = Query(None, description="Region ID filter"),
    bbox: str | None = Query(None, description="Bounding box filter minLon,minLat,maxLon,maxLat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
    h3_res: int = Query(5, ge=1, le=10, description="Requested H3 resolution (data is served at its native resolution)"),
) -> dict[str, Any]:
    """H3-cell aggregated harmonized activity. Served at the mart's native resolution; no values are invented."""
    region_id = _clean_param(region_id, None)
    bbox = _clean_param(bbox, None)
    polygon = _clean_param(polygon, None)
    start = _clean_param(start, None)
    end = _clean_param(end, None)
    requested_res = int(_clean_param(h3_res, 5))
    data_res = int(get_harmonization_config().get("h3_resolution", 5))

    area_type, cells_list, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon, h3_res=data_res
    )

    clauses = ["1=1"]
    params: list[Any] = []
    if cells_list is not None:
        if len(cells_list) == 0:
            meta = make_meta(reliability="insufficient", warnings=["Area contains no valid grid cells."])
            return {"data": {"h3_resolution": data_res, "cells": []}, "meta": meta}
        clauses.append("h3_cell IN (SELECT unnest(?::VARCHAR[]))")
        params.append(cells_list)
    if start:
        clauses.append("acq_date >= CAST(? AS DATE)")
        params.append(start)
    if end:
        clauses.append("acq_date <= CAST(? AS DATE)")
        params.append(end)

    query = f"""
        SELECT h3_cell,
               SUM(harmonized_value) AS harmonized_value,
               SUM(harmonized_lower) AS lower,
               SUM(harmonized_upper) AS upper,
               SUM(modis_observed) AS modis_observed,
               SUM(viirs_observed) AS viirs_observed,
               BOOL_OR(is_provisional) AS is_provisional,
               BOOL_AND(value_type = 'observed') AS all_observed
        FROM harmonized_cell_day
        WHERE {" AND ".join(clauses)}
        GROUP BY h3_cell
        ORDER BY harmonized_value DESC NULLS LAST
        LIMIT 5000
    """
    try:
        df = repo.con.execute(query, params).df()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"harmonized cell data unavailable: {e}")

    def num(x: Any) -> float | None:
        return None if x is None or x != x else round(float(x), 2)

    cells: list[dict[str, Any]] = []
    total_val = 0.0
    is_any_prov = False
    all_obs = True
    for _, r in df.iterrows():
        val, lo, up = num(r["harmonized_value"]), num(r["lower"]), num(r["upper"])
        if val is not None and lo == up == val:
            lo = up = None  # zero-width: no calibration interval applies to direct observations
        prov = bool(r["is_provisional"]) if r["is_provisional"] is not None else False
        obs_only = bool(r["all_observed"]) if r["all_observed"] is not None else False
        is_any_prov = is_any_prov or prov
        all_obs = all_obs and obs_only
        total_val += val or 0.0
        cells.append({
            "h3_cell": str(r["h3_cell"]),
            "harmonized_value": val,
            "lower": lo,
            "upper": up,
            "modis_observed": num(r["modis_observed"]),
            "viirs_observed": num(r["viirs_observed"]),
            "is_provisional": prov,
            "reliability": ("provisional" if prov else "direct_observation") if obs_only else None,
        })

    eff_series, reliability, _rl, _ru, warnings = evaluate_series_and_uncertainty(
        expected_count=total_val, is_drawn_area=is_drawn_area, requested_series="harmonized"
    )
    warnings = list(warnings or [])
    if cells and all_obs:
        reliability = "provisional" if is_any_prov else "direct_observation"
    elif not cells:
        reliability = "insufficient"
    if requested_res != data_res:
        warnings.append(f"Requested H3 resolution {requested_res}; data is served at its native resolution {data_res}.")
    warnings.append("Cell-level harmonized value equals the NOAA-20 observation; no MODIS conversion is applied.")

    meta = make_meta(series=eff_series, method="identity", is_provisional=is_any_prov,
                     reliability=reliability, warnings=warnings)
    return {"data": {"h3_resolution": data_res, "cells": cells, "reliability": reliability,
                     "warning": warnings[0] if warnings else None}, "meta": meta}