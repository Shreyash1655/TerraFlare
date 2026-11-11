"""Core API route: /api/v1/calendar."""

from __future__ import annotations

import calendar as pycalendar
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.regions import load_regions

router = APIRouter(tags=["calendar"])
repo = DuckDBRepository()


class CalendarDay(BaseModel):
    date: str
    harmonized_value: float
    lower: float
    upper: float
    data_flag: str
    is_provisional: bool = False


class CalendarResponse(BaseModel):
    year: int
    region_id: str
    unit: str
    days: list[CalendarDay]


@router.get("/calendar", response_model=CalendarResponse)
def get_calendar(
    region_id: str = Query("india", description="Region ID"),
    year: int | None = Query(None, description="Calendar year (default: latest year in dataset)"),
) -> dict[str, Any]:
    """Return 365 daily harmonized values for a region and year."""
    regions = load_regions()
    if region_id not in regions:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")

    # Determine year if not provided
    if year is None:
        try:
            max_dt = repo.con.execute(
                f"SELECT MAX(acq_date) FROM harmonized_cell_day WHERE region_id = '{region_id}'"
            ).fetchone()[0]
            year = max_dt.year if max_dt is not None else 2026
        except Exception:
            year = 2026

    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"

    query = f"""
        SELECT
            acq_date,
            ROUND(SUM(harmonized_value), 2) AS harmonized_value,
            ROUND(SUM(harmonized_lower), 2) AS lower,
            ROUND(SUM(harmonized_upper), 2) AS upper,
            BOOL_OR(is_provisional) AS is_provisional
        FROM harmonized_cell_day
        WHERE region_id = '{region_id}'
          AND acq_date >= '{start_date_str}'
          AND acq_date <= '{end_date_str}'
        GROUP BY acq_date
        ORDER BY acq_date ASC
    """

    data_by_date = {}
    try:
        df = repo.con.execute(query).df()
        if not df.empty:
            for _, r in df.iterrows():
                d_str = str(r["acq_date"])
                data_by_date[d_str] = {
                    "harmonized_value": float(r["harmonized_value"]),
                    "lower": float(r["lower"]) if r["lower"] is not None else round(float(r["harmonized_value"]) * 0.8, 2),
                    "upper": float(r["upper"]) if r["upper"] is not None else round(float(r["harmonized_value"]) * 1.2, 2),
                    "is_provisional": bool(r["is_provisional"]) if r["is_provisional"] is not None else False,
                }
    except Exception:
        pass

    # Build 365 / 366 calendar days
    days_list = []
    is_leap = pycalendar.isleap(year)
    total_days = 366 if is_leap else 365
    cur_date = date(year, 1, 1)

    for _ in range(total_days):
        d_str = cur_date.isoformat()
        if d_str in data_by_date:
            info = data_by_date[d_str]
            days_list.append(
                CalendarDay(
                    date=d_str,
                    harmonized_value=info["harmonized_value"],
                    lower=info["lower"],
                    upper=info["upper"],
                    data_flag="recorded",
                    is_provisional=info["is_provisional"],
                )
            )
        else:
            days_list.append(
                CalendarDay(
                    date=d_str,
                    harmonized_value=0.0,
                    lower=0.0,
                    upper=0.0,
                    data_flag="no_detections_recorded",
                    is_provisional=False,
                )
            )
        cur_date += timedelta(days=1)

    return {
        "year": year,
        "region_id": region_id,
        "unit": "harmonized activity index",
        "days": days_list,
    }
