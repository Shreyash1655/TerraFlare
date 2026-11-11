"""Core API route: /api/v1/export/csv."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.regions import load_regions

router = APIRouter(prefix="/export", tags=["export"])
repo = DuckDBRepository()


@router.get("/csv")
def export_csv(
    dataset: str = Query(..., pattern="^(monthly|calendar|hotspots|comparison)$", description="Dataset to export"),
    region_id: str = Query("india", description="Region ID"),
    year: int | None = Query(None, description="Filter year"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
) -> Response:
    """Stream dataset as a downloadable CSV."""
    regions = load_regions()
    if region_id not in regions:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")

    output_df = pd.DataFrame()

    if dataset == "monthly":
        query = f"""
            SELECT
                region_id,
                strftime(acq_date, '%Y-%m') AS year_month,
                'harmonized' AS value_type,
                'HARMONIZED' AS sensor_family,
                ROUND(SUM(harmonized_value), 2) AS value,
                ROUND(SUM(harmonized_lower), 2) AS lower,
                ROUND(SUM(harmonized_upper), 2) AS upper,
                '1.0' AS data_version
            FROM harmonized_cell_day
            WHERE region_id = '{region_id}'
            GROUP BY region_id, year_month
            ORDER BY year_month ASC
        """
        try:
            output_df = repo.con.execute(query).df()
        except Exception:
            cols = ["region_id", "year_month", "value_type", "sensor_family", "value", "lower", "upper", "data_version"]
            output_df = pd.DataFrame(columns=cols)

    elif dataset == "calendar":
        target_year = year or 2026
        query = f"""
            SELECT
                acq_date::VARCHAR AS date,
                ROUND(SUM(harmonized_value), 2) AS harmonized_value,
                ROUND(SUM(harmonized_lower), 2) AS lower,
                ROUND(SUM(harmonized_upper), 2) AS upper,
                'recorded' AS data_flag,
                BOOL_OR(is_provisional) AS is_provisional
            FROM harmonized_cell_day
            WHERE region_id = '{region_id}'
              AND EXTRACT(year FROM acq_date) = {target_year}
            GROUP BY acq_date
            ORDER BY acq_date ASC
        """
        try:
            output_df = repo.con.execute(query).df()
        except Exception:
            cols = ["date", "harmonized_value", "lower", "upper", "data_flag", "is_provisional"]
            output_df = pd.DataFrame(columns=cols)

    elif dataset == "hotspots":
        reg_bb = regions[region_id].bbox
        clauses = [
            "is_valid = true",
            f"lon >= {reg_bb.min_lon} AND lon <= {reg_bb.max_lon} AND lat >= {reg_bb.min_lat} AND lat <= {reg_bb.max_lat}",
        ]
        if start:
            clauses.append(f"acq_date >= '{start}'")
        if end:
            clauses.append(f"acq_date <= '{end}'")
        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT
                obs_id, sensor_family, platform, acq_datetime_utc,
                confidence_class, frp_mw,
                (UPPER(processing_stream) = 'NRT') AS is_provisional,
                lon, lat
            FROM obs_clean
            WHERE {where_sql}
            ORDER BY acq_date DESC
            LIMIT 50000
        """
        try:
            output_df = repo.con.execute(query).df()
        except Exception:
            cols = ["obs_id", "sensor_family", "platform", "acq_datetime_utc", "confidence_class", "frp_mw", "is_provisional", "lon", "lat"]
            output_df = pd.DataFrame(columns=cols)

    elif dataset == "comparison":
        clauses = [f"region_id = '{region_id}'"]
        if start:
            clauses.append(f"acq_date >= '{start}'")
        if end:
            clauses.append(f"acq_date <= '{end}'")
        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT
                strftime(acq_date, '%G-W%V') AS period,
                ROUND(SUM(modis_observed), 2) AS modis_observed,
                ROUND(SUM(viirs_observed), 2) AS viirs_observed,
                ROUND(SUM(harmonized_value), 2) AS harmonized_value,
                ROUND(SUM(harmonized_lower), 2) AS lower,
                ROUND(SUM(harmonized_upper), 2) AS upper
            FROM harmonized_cell_day
            WHERE {where_sql}
            GROUP BY period
            ORDER BY period ASC
        """
        try:
            output_df = repo.con.execute(query).df()
        except Exception:
            cols = ["period", "modis_observed", "viirs_observed", "harmonized_value", "lower", "upper"]
            output_df = pd.DataFrame(columns=cols)

    buf = io.StringIO()
    output_df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")

    filename = f"terraflare_{dataset}_{region_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
