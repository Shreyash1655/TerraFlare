"""Core API routes: /api/v1/hotspots and /api/v1/hotspots/cells wrapped in common envelope."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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
    h3_res: int = Query(6, ge=1, le=10, description="H3 cell resolution"),
) -> dict[str, Any]:
    """Query H3-cell aggregated harmonized activity wrapped in common envelope."""
    region_id = _clean_param(region_id, None)
    bbox = _clean_param(bbox, None)
    polygon = _clean_param(polygon, None)
    start = _clean_param(start, None)
    end = _clean_param(end, None)
    h3_res = int(_clean_param(h3_res, 6))

    area_type, cells_list, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon, h3_res=h3_res
    )

    clauses = ["1=1"]
    params: list[Any] = []

    if cells_list is not None:
        if len(cells_list) == 0:
            cells_data = {"h3_resolution": h3_res, "cells": []}
            meta = make_meta(reliability="insufficient", warnings=["Area contains no valid grid cells."])
            return {"data": cells_data, "meta": meta}
        clauses.append("h3_cell IN (SELECT unnest(?::VARCHAR[]))")
        params.append(cells_list)
    elif region_id and region_id.lower() not in ("india", "all"):
        clauses.append(f"region_id = '{region_id}'")

    if start:
        clauses.append(f"acq_date >= '{start}'")
    if end:
        clauses.append(f"acq_date <= '{end}'")

    where_sql = " AND ".join(clauses)
    query = f"""
        SELECT
            h3_cell,
            ROUND(SUM(CASE WHEN acq_date >= '2012-01-20' AND viirs_platform = 'none' THEN 0.0 ELSE harmonized_value END), 2) AS harmonized_value,
            ROUND(SUM(harmonized_lower), 2) AS lower,
            ROUND(SUM(harmonized_upper), 2) AS upper,
            ROUND(SUM(modis_observed), 2) AS modis_observed,
            ROUND(SUM(viirs_observed), 2) AS viirs_observed,
            BOOL_OR(is_provisional) AS is_provisional
        FROM harmonized_cell_day
        WHERE {where_sql}
        GROUP BY h3_cell
        ORDER BY harmonized_value DESC
        LIMIT 5000
    """

    try:
        df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
    except Exception:
        df = None

    cells = []
    total_val = 0.0
    is_any_prov = False

    if df is not None and not df.empty:
        for _, r in df.iterrows():
            val = float(r["harmonized_value"])
            total_val += val
            _, _, rel = interval_for(val)
            prov = bool(r["is_provisional"]) if r["is_provisional"] is not None else False
            if prov:
                is_any_prov = True
            cells.append({
                "h3_cell": str(r["h3_cell"]),
                "harmonized_value": val,
                "lower": float(r["lower"]) if r["lower"] is not None else round(val * 0.8, 2),
                "upper": float(r["upper"]) if r["upper"] is not None else round(val * 1.2, 2),
                "modis_observed": float(r["modis_observed"]) if r["modis_observed"] is not None else 0.0,
                "viirs_observed": float(r["viirs_observed"]) if r["viirs_observed"] is not None else 0.0,
                "is_provisional": prov,
                "reliability": rel,
            })

    eff_series, reliability, rel_l, rel_u, warnings = evaluate_series_and_uncertainty(
        expected_count=total_val,
        is_drawn_area=is_drawn_area,
        requested_series="harmonized",
    )

    cells_data = {
        "h3_resolution": h3_res,
        "cells": cells,
        "reliability": reliability,
        "warning": warnings[0] if warnings else None,
    }

    meta = make_meta(
        series=eff_series,
        method="stratified_ratio",
        is_provisional=is_any_prov,
        reliability=reliability,
        warnings=warnings,
    )
    return {"data": cells_data, "meta": meta}
