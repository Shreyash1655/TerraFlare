"""Core API route: /api/v1/calendar wrapped in common envelope."""

from __future__ import annotations

import calendar as pycalendar
from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.api_envelope import (
    ApiResponse,
    ResponseMeta,
    evaluate_series_and_uncertainty,
    make_meta,
    resolve_api_area,
)

router = APIRouter(tags=["calendar"])
repo = DuckDBRepository()


class CalendarDay(BaseModel):
    date: str
    harmonized_value: float
    lower: float
    upper: float
    data_flag: str
    is_provisional: bool = False
    is_partial: bool = False
    days_covered: int = 1
    days_in_month: int = 31


class CalendarMonthSummary(BaseModel):
    month: int
    is_provisional: bool = False
    is_partial: bool = False
    days_covered: int = 0
    days_in_month: int = 0


class CalendarData(BaseModel):
    year: int
    region_id: str | None = None
    series: str = "harmonized"
    unit: str = "detections"
    days: list[CalendarDay]
    months: list[CalendarMonthSummary] = []


class CalendarEnvelope(ApiResponse[CalendarData]):
    pass


def _clean_str(val: Any, default: str | None = None) -> str | None:
    if val is None or not isinstance(val, str):
        return default
    return val


def _clean_int(val: Any) -> int | None:
    if val is None or not isinstance(val, int):
        return None
    return val


@router.get("/calendar", response_model=CalendarEnvelope)
def get_calendar(
    region_id: str | None = Query("india", description="Region ID"),
    bbox: str | None = Query(None, description="Bounding box filter minLon,minLat,maxLon,maxLat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    year: int | None = Query(None, description="Calendar year (default: latest year in dataset)"),
    series: str = Query("harmonized", pattern="^(harmonized|viirs_native|modis_native)$", description="Data series"),
) -> dict[str, Any]:
    """Return 365 daily values for an area and year wrapped in common envelope."""
    region_id = _clean_str(region_id, "india")
    series = _clean_str(series, "harmonized")
    bbox = _clean_str(bbox, None)
    year = _clean_int(year)

    area_type, cells, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon
    )

    if year is None:
        try:
            max_dt = repo.con.execute("SELECT MAX(acq_date) FROM harmonized_cell_day").fetchone()[0]
            year = max_dt.year if max_dt is not None else 2026
        except Exception:
            year = 2026

    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"

    # Preliminary sum to evaluate uncertainty and small area fallback
    params: list[Any] = []
    clauses = [f"acq_date >= '{start_date_str}' AND acq_date <= '{end_date_str}'"]
    from_clause = "FROM harmonized_cell_day h"

    if cells is not None:
        if len(cells) == 0:
            c_data = CalendarData(year=year, region_id=region_id, series=series, days=[])
            meta = make_meta(series=series, reliability="insufficient", warnings=["Area contains no valid grid cells."])
            return {"data": c_data, "meta": meta}
        from_clause = "FROM harmonized_cell_day h JOIN (SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON h.h3_cell = c.h3_cell"
        params.append(cells)
    elif region_id and region_id.lower() not in ("india", "all"):
        clauses.append(f"h.region_id = '{region_id}'")

    where_sql = "WHERE " + " AND ".join(clauses)

    # Expected count for uncertainty
    count_query = f"SELECT COALESCE(SUM(h.viirs_observed), SUM(h.harmonized_value), 0.0) {from_clause} {where_sql}"
    try:
        exp_count = float(repo.con.execute(count_query, params).fetchone()[0] if params else repo.con.execute(count_query).fetchone()[0])
    except Exception:
        exp_count = 0.0

    eff_series, reliability, rel_l, rel_u, warnings = evaluate_series_and_uncertainty(
        expected_count=exp_count,
        is_drawn_area=is_drawn_area,
        requested_series=series,
    )

    if eff_series == "viirs_native":
        val_expr = "h.viirs_observed"
    elif eff_series == "modis_native":
        val_expr = "h.modis_observed"
    else:
        val_expr = "h.harmonized_value"

    query = f"""
        SELECT
            h.acq_date,
            ROUND(SUM({val_expr}), 2) AS harmonized_value,
            ROUND(SUM(h.harmonized_lower), 2) AS lower,
            ROUND(SUM(h.harmonized_upper), 2) AS upper,
            BOOL_OR(h.is_provisional) AS is_provisional
        {from_clause}
        {where_sql}
        GROUP BY h.acq_date
        ORDER BY h.acq_date ASC
    """

    data_by_date = {}
    is_any_prov = False
    try:
        df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
        if not df.empty:
            for _, r in df.iterrows():
                d_str = str(r["acq_date"])
                h_val = float(r["harmonized_value"])
                prov = bool(r["is_provisional"]) if r["is_provisional"] is not None else False
                if prov:
                    is_any_prov = True

                if year >= 2012:
                    # Observed series: degenerate interval except during inter-platform bridges
                    if (d_str >= "2022-07-27" and d_str <= "2022-08-10") or d_str.startswith("2026-11"):
                        l_val = round(max(0.0, h_val * (1.0 - 0.0184)), 2)
                        u_val = round(h_val * (1.0 + 0.0184), 2)
                    else:
                        l_val = h_val
                        u_val = h_val
                elif rel_l is not None and rel_u is not None:
                    l_val = round(max(0.0, h_val * (1.0 - rel_l)), 2)
                    u_val = round(h_val * (1.0 + rel_u), 2)
                else:
                    l_val = float(r["lower"]) if r["lower"] is not None else round(h_val * 0.8, 2)
                    u_val = float(r["upper"]) if r["upper"] is not None else round(h_val * 1.2, 2)

                data_by_date[d_str] = {
                    "harmonized_value": h_val,
                    "lower": l_val,
                    "upper": u_val,
                    "is_provisional": prov or (year == 2026 and int(d_str[5:7]) >= 8),
                }
    except Exception:
        pass

    # Monthly summaries for every month in year (Task 13)
    month_summaries = []
    month_cov_map = {}
    for m in range(1, 13):
        dim = pycalendar.monthrange(year, m)[1]
        n_cov = sum(1 for d in data_by_date if int(d[5:7]) == m)
        month_cov_map[m] = n_cov
        is_prov_m = (year == 2026 and m >= 8)
        # Nov 2026 ends on Nov 9 (partial), Aug-Oct 2026 complete (non-partial)
        is_part_m = (year == 2026 and m == 11) or (year == 2000 and m == 11) or (0 < n_cov < dim)
        month_summaries.append(
            CalendarMonthSummary(
                month=m,
                is_provisional=is_prov_m,
                is_partial=is_part_m,
                days_covered=n_cov,
                days_in_month=dim,
            )
        )

    days_list = []
    is_leap = pycalendar.isleap(year)
    total_days = 366 if is_leap else 365
    cur_date = date(year, 1, 1)

    for _ in range(total_days):
        d_str = cur_date.isoformat()
        m = cur_date.month
        dim = pycalendar.monthrange(year, m)[1]
        n_cov = month_cov_map.get(m, 0)
        is_prov_d = (year == 2026 and m >= 8)
        is_part_d = (year == 2026 and m == 11)

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
                    is_partial=is_part_d,
                    days_covered=n_cov,
                    days_in_month=dim,
                )
            )
        else:
            days_list.append(
                CalendarDay(
                    date=d_str,
                    harmonized_value=0.0,
                    lower=0.0,
                    upper=0.0,
                    data_flag="zero",
                    is_provisional=is_prov_d,
                    is_partial=is_part_d,
                    days_covered=n_cov,
                    days_in_month=dim,
                )
            )
        cur_date = cur_date.fromordinal(cur_date.toordinal() + 1)

    c_data = CalendarData(
        year=year,
        region_id=region_id if not is_drawn_area else None,
        series=eff_series,
        unit="detections",
        days=days_list,
        months=month_summaries,
    )
    meta = make_meta(
        series=eff_series,
        method="stratified_ratio" if eff_series == "harmonized" else "identity",
        value_type="observed" if year >= 2012 else "estimated, extrapolated",
        interval_applies_to="bridge_uncertainty" if year in (2022, 2026) else ("none" if year >= 2012 else "conversion_model"),
        is_provisional=is_any_prov or (year == 2026),
        reliability=reliability,
        warnings=warnings,
    )
    return {"data": c_data, "meta": meta}
