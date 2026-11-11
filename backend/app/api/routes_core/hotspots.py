"""Core API routes: /api/v1/hotspots and /api/v1/hotspots/cells."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.harmonization.uncertainty import interval_for
from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.regions import load_regions

router = APIRouter(tags=["hotspots"])
repo = DuckDBRepository()


def parse_bbox_string(bbox_str: str) -> tuple[float, float, float, float]:
    """Parse comma-separated 'minLon,minLat,maxLon,maxLat' string."""
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError()
        min_lon, min_lat, max_lon, max_lat = parts
        if min_lon > max_lon or min_lat > max_lat:
            raise ValueError()
        return min_lon, min_lat, max_lon, max_lat
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox format. Expected 'minLon,minLat,maxLon,maxLat' with min <= max.",
        )


def _clean_param(val: Any, default: Any = None) -> Any:
    if hasattr(val, "default"):
        return val.default if val.default is not ... else default
    return val if val is not None else default


@router.get("/hotspots")
def get_hotspots(
    region_id: str | None = Query(None, description="Region ID filter"),
    bbox: str | None = Query(None, description="Bounding box filter minLon,minLat,maxLon,maxLat"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
    sensors: str | None = Query(None, description="Comma-separated sensor families (MODIS,VIIRS)"),
    confidence: str | None = Query(None, description="Minimum confidence class (low, nominal, high)"),
    limit: int = Query(5000, ge=1, le=10000, description="Maximum number of points to return"),
) -> dict[str, Any]:
    """Query hotspot point detections as GeoJSON FeatureCollection."""
    region_id = _clean_param(region_id, None)
    bbox = _clean_param(bbox, None)
    start = _clean_param(start, None)
    end = _clean_param(end, None)
    sensors = _clean_param(sensors, None)
    confidence = _clean_param(confidence, None)
    limit = int(_clean_param(limit, 5000))

    clauses = ["is_valid = true"]
    is_drawn_area = bool(bbox)

    if bbox:
        min_lon, min_lat, max_lon, max_lat = parse_bbox_string(bbox)
        clauses.append(f"lon >= {min_lon} AND lon <= {max_lon} AND lat >= {min_lat} AND lat <= {max_lat}")
    elif region_id:
        regions = load_regions()
        if region_id not in regions:
            raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")
        reg_bb = regions[region_id].bbox
        clauses.append(
            f"lon >= {reg_bb.min_lon} AND lon <= {reg_bb.max_lon} AND "
            f"lat >= {reg_bb.min_lat} AND lat <= {reg_bb.max_lat}"
        )

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
        df = repo.con.execute(query).df()
    except Exception:
        df = None

    features = []
    truncated = False
    total_count = 0

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
            # Per-source provisional check: NRT stream or null/missing SP
            stream_val = str(row.get("processing_stream", "")).upper()
            is_prov = stream_val == "NRT"

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

    resp: dict[str, Any] = {
        "type": "FeatureCollection",
        "truncated": truncated,
        "features": features,
    }

    # Task 10 addendum: uncertainty and reliability for drawn area
    if is_drawn_area:
        expected = float(len(features))
        rel_l, rel_u, reliability = interval_for(expected)
        resp["reliability"] = reliability
        if rel_l is not None and rel_u is not None:
            resp["uncertainty_interval"] = [
                round(max(0.0, expected * (1.0 - rel_l)), 1),
                round(expected * (1.0 + rel_u), 1),
            ]
        else:
            resp["uncertainty_interval"] = None
        if reliability in ("low", "insufficient") or expected < 10:
            resp["warning"] = "Area is small: uncertainty intervals are wide and satellite detection intermittency is high"

    return resp


@router.get("/hotspots/cells")
def get_hotspot_cells(
    region_id: str | None = Query(None, description="Region ID filter"),
    bbox: str | None = Query(None, description="Bounding box filter minLon,minLat,maxLon,maxLat"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
    h3_res: int = Query(6, ge=1, le=10, description="H3 cell resolution"),
) -> dict[str, Any]:
    """Query H3-cell aggregated harmonized activity."""
    region_id = _clean_param(region_id, None)
    bbox = _clean_param(bbox, None)
    start = _clean_param(start, None)
    end = _clean_param(end, None)
    h3_res = int(_clean_param(h3_res, 6))

    clauses = ["1=1"]
    is_drawn_area = bool(bbox)

    if bbox:
        min_lon, min_lat, max_lon, max_lat = parse_bbox_string(bbox)
        # Filter harmonized_cell_day using joined obs_clean or cell day bbox
        clauses.append(f"h3_cell IN (SELECT DISTINCT h3_cell FROM obs_clean WHERE lon >= {min_lon} AND lon <= {max_lon} AND lat >= {min_lat} AND lat <= {max_lat} AND is_valid = true)")
    elif region_id:
        regions = load_regions()
        if region_id not in regions:
            raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")
        clauses.append(f"region_id = '{region_id}'")

    if start:
        clauses.append(f"acq_date >= '{start}'")
    if end:
        clauses.append(f"acq_date <= '{end}'")

    where_sql = " AND ".join(clauses)
    query = f"""
        SELECT
            h3_cell,
            ROUND(SUM(harmonized_value), 2) AS harmonized_value,
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
        df = repo.con.execute(query).df()
    except Exception:
        df = None

    cells = []
    total_val = 0.0
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            val = float(r["harmonized_value"])
            total_val += val
            _, _, rel = interval_for(val)
            cells.append({
                "h3_cell": str(r["h3_cell"]),
                "harmonized_value": val,
                "lower": float(r["lower"]) if r["lower"] is not None else round(val * 0.8, 2),
                "upper": float(r["upper"]) if r["upper"] is not None else round(val * 1.2, 2),
                "modis_observed": float(r["modis_observed"]) if r["modis_observed"] is not None else 0.0,
                "viirs_observed": float(r["viirs_observed"]) if r["viirs_observed"] is not None else 0.0,
                "is_provisional": bool(r["is_provisional"]) if r["is_provisional"] is not None else False,
                "reliability": rel,
            })

    resp: dict[str, Any] = {
        "h3_resolution": h3_res,
        "cells": cells,
    }

    if is_drawn_area:
        _, _, overall_rel = interval_for(total_val)
        resp["reliability"] = overall_rel
        if overall_rel in ("low", "insufficient") or total_val < 10:
            resp["warning"] = "Area is small: uncertainty intervals are wide and satellite detection intermittency is high"

    return resp
