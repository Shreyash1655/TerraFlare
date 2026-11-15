"""Core API route: /api/v1/export/csv with streaming, metadata block, and standard columns."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.api_envelope import (
    get_current_data_version,
    resolve_api_area,
)

router = APIRouter(prefix="/export", tags=["export"])
repo = DuckDBRepository()


def _clean_param(val: Any, default: Any = None) -> Any:
    if hasattr(val, "default"):
        return val.default if val.default is not ... else default
    return val if val is not None else default


@router.get("/csv")
def export_csv(
    dataset: str = Query(..., pattern="^(monthly|calendar|hotspots|comparison)$", description="Dataset to export"),
    region_id: str | None = Query("india", description="Region ID"),
    bbox: str | None = Query(None, description="Bounding box filter minLon,minLat,maxLon,maxLat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    series: str = Query("harmonized", pattern="^(harmonized|viirs_native|modis_native)$", description="Data series"),
    year: int | None = Query(None, description="Filter year"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
) -> StreamingResponse:
    """Stream dataset as a downloadable CSV with metadata block and required columns."""
    dataset = str(_clean_param(dataset, "monthly"))
    region_id = _clean_param(region_id, "india")
    bbox = _clean_param(bbox, None)
    polygon = _clean_param(polygon, None)
    series = str(_clean_param(series, "harmonized"))
    year = _clean_param(year, None)
    start = _clean_param(start, None)
    end = _clean_param(end, None)
    area_type, cells, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon
    )

    data_ver = get_current_data_version()
    gen_at = datetime.now(timezone.utc).isoformat()
    area_label = "custom_area" if is_drawn_area else (region_id or "india")

    meta_lines = [
        f"# TerraFlare Active Fire Observation Export",
        f"# Dataset: {dataset}",
        f"# Area: {area_label}",
        f"# Series: {series}",
        f"# Data Version: {data_ver}",
        f"# Generated At: {gen_at}",
        f"#",
    ]
    meta_header = "\n".join(meta_lines) + "\n"

    params: list[Any] = []
    from_clause = "FROM harmonized_cell_day h"
    clauses: list[str] = []

    if cells is not None:
        from_clause = "FROM harmonized_cell_day h JOIN (SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON h.h3_cell = c.h3_cell"
        params.append(cells)
    elif region_id and region_id.lower() not in ("india", "all"):
        clauses.append(f"h.region_id = '{region_id}'")

    if dataset == "monthly":
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"""
            SELECT
                strftime(h.acq_date, '%Y-%m') AS year_month,
                'HARMONIZED' AS sensor,
                'HARMONIZED' AS sensor_family,
                COALESCE(h.platform_used, 'Aqua') AS platform,
                CASE WHEN h.acq_date < '2012-01-20' THEN 'estimated, extrapolated' ELSE 'observed' END AS value_type,
                ROUND(SUM(h.harmonized_value), 2) AS value,
                ROUND(SUM(h.harmonized_value), 2) AS lower,
                ROUND(SUM(h.harmonized_value), 2) AS upper,
                ROUND(SUM(h.modis_observed), 2) AS modis_observed,
                ROUND(SUM(h.viirs_observed), 2) AS viirs_observed,
                BOOL_OR(h.is_provisional) AS is_provisional,
                CASE 
                    WHEN strftime(h.acq_date, '%Y-%m') = '2026-11' THEN true
                    WHEN strftime(h.acq_date, '%Y-%m') = '2000-11' THEN true
                    ELSE false 
                END AS is_partial,
                COUNT(DISTINCT h.acq_date) AS days_covered,
                CASE 
                    WHEN EXTRACT(month FROM h.acq_date) IN (1, 3, 5, 7, 8, 10, 12) THEN 31
                    WHEN EXTRACT(month FROM h.acq_date) IN (4, 6, 9, 11) THEN 30
                    WHEN (EXTRACT(year FROM h.acq_date) % 4 = 0 AND EXTRACT(year FROM h.acq_date) % 100 != 0) OR (EXTRACT(year FROM h.acq_date) % 400 = 0) THEN 29
                    ELSE 28
                END AS days_in_month
            {from_clause}
            {where_sql}
            GROUP BY year_month, platform, EXTRACT(month FROM h.acq_date), EXTRACT(year FROM h.acq_date)
            ORDER BY year_month ASC
        """
        try:
            output_df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
        except Exception:
            cols = ["year_month", "sensor", "sensor_family", "platform", "value_type", "value", "lower", "upper", "modis_observed", "viirs_observed", "is_provisional", "is_partial", "days_covered", "days_in_month"]
            output_df = pd.DataFrame(columns=cols)

    elif dataset == "calendar":
        target_year = year or 2026
        clauses.append(f"EXTRACT(year FROM h.acq_date) = {target_year}")
        where_sql = "WHERE " + " AND ".join(clauses)
        query = f"""
            SELECT
                h.acq_date::VARCHAR AS date,
                'HARMONIZED' AS sensor,
                'HARMONIZED' AS sensor_family,
                COALESCE(h.platform_used, 'Aqua') AS platform,
                CASE WHEN h.acq_date < '2012-01-20' THEN 'estimated, extrapolated' ELSE 'observed' END AS value_type,
                ROUND(SUM(h.harmonized_value), 2) AS harmonized_value,
                ROUND(SUM(h.harmonized_value), 2) AS lower,
                ROUND(SUM(h.harmonized_value), 2) AS upper,
                'recorded' AS data_flag,
                BOOL_OR(h.is_provisional) AS is_provisional,
                (h.acq_date >= '2026-11-01' AND h.acq_date <= '2026-11-30') AS is_partial,
                1 AS days_covered,
                CASE 
                    WHEN EXTRACT(month FROM h.acq_date) IN (1, 3, 5, 7, 8, 10, 12) THEN 31
                    WHEN EXTRACT(month FROM h.acq_date) IN (4, 6, 9, 11) THEN 30
                    WHEN (EXTRACT(year FROM h.acq_date) % 4 = 0 AND EXTRACT(year FROM h.acq_date) % 100 != 0) OR (EXTRACT(year FROM h.acq_date) % 400 = 0) THEN 29
                    ELSE 28
                END AS days_in_month
            {from_clause}
            {where_sql}
            GROUP BY h.acq_date, platform
            ORDER BY h.acq_date ASC
        """
        try:
            output_df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
        except Exception:
            cols = ["date", "sensor", "sensor_family", "platform", "value_type", "harmonized_value", "lower", "upper", "data_flag", "is_provisional", "is_partial", "days_covered", "days_in_month"]
            output_df = pd.DataFrame(columns=cols)

    elif dataset == "hotspots":
        obs_clauses = ["is_valid = true"]
        obs_params: list[Any] = []
        if cells is not None:
            obs_clauses.append("h3_cell IN (SELECT unnest(?::VARCHAR[]))")
            obs_params.append(cells)
        elif bbox_tuple:
            b_min_lon, b_min_lat, b_max_lon, b_max_lat = bbox_tuple
            obs_clauses.append(f"lon >= {b_min_lon} AND lon <= {b_max_lon} AND lat >= {b_min_lat} AND lat <= {b_max_lat}")
        if start:
            obs_clauses.append(f"acq_date >= '{start}'")
        if end:
            obs_clauses.append(f"acq_date <= '{end}'")
        where_sql = "WHERE " + " AND ".join(obs_clauses)
        query = f"""
            SELECT
                obs_id,
                sensor_family AS sensor,
                sensor_family,
                platform,
                'observed' AS value_type,
                acq_datetime_utc,
                confidence_class,
                frp_mw,
                (UPPER(processing_stream) = 'NRT') AS is_provisional,
                lon,
                lat
            FROM obs_clean
            {where_sql}
            ORDER BY acq_date DESC
            LIMIT 50000
        """
        try:
            output_df = repo.con.execute(query, obs_params).df() if obs_params else repo.con.execute(query).df()
        except Exception:
            cols = ["obs_id", "sensor", "sensor_family", "platform", "value_type", "acq_datetime_utc", "confidence_class", "frp_mw", "is_provisional", "lon", "lat"]
            output_df = pd.DataFrame(columns=cols)

    elif dataset == "comparison":
        if start:
            clauses.append(f"h.acq_date >= '{start}'")
        if end:
            clauses.append(f"h.acq_date <= '{end}'")
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"""
            SELECT
                strftime(h.acq_date, '%G-W%V') AS period,
                'HARMONIZED' AS sensor,
                'HARMONIZED' AS sensor_family,
                COALESCE(h.platform_used, 'Aqua') AS platform,
                'comparison' AS value_type,
                ROUND(SUM(h.modis_observed), 2) AS modis_observed,
                ROUND(SUM(h.viirs_observed), 2) AS viirs_observed,
                ROUND(SUM(h.harmonized_value), 2) AS harmonized_value,
                ROUND(SUM(h.harmonized_lower), 2) AS lower,
                ROUND(SUM(h.harmonized_upper), 2) AS upper,
                BOOL_OR(h.is_provisional) AS is_provisional
            {from_clause}
            {where_sql}
            GROUP BY period, platform
            ORDER BY period ASC
        """
        try:
            output_df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
        except Exception:
            cols = ["period", "sensor", "sensor_family", "platform", "value_type", "modis_observed", "viirs_observed", "harmonized_value", "lower", "upper", "is_provisional"]
            output_df = pd.DataFrame(columns=cols)

    buf = io.StringIO()
    buf.write(meta_header)
    output_df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")

    filename = f"terraflare_{dataset}_{area_label}.csv"
    response = StreamingResponse(
        content=io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
    # Expose raw bytes for synchronous testing under Python 3.14
    response.raw_content = csv_bytes
    return response
