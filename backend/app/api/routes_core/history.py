"""Core API routes: /api/v1/history/yearly, /api/v1/history/monthly, /api/v1/history/current-vs-median wrapped in common envelope."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.analytics.area_monthly import (
    aggregate_area_monthly,
    compute_current_vs_median,
)
from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.api_envelope import (
    ApiResponse,
    ResponseMeta,
    evaluate_series_and_uncertainty,
    make_meta,
    resolve_api_area,
)

router = APIRouter(prefix="/history", tags=["history"])
repo = DuckDBRepository()


class YearlyHistoryItem(BaseModel):
    year: int
    harmonized_value: float
    lower: float
    upper: float
    modis_observed: float
    viirs_observed: float
    sensor_mix: list[str]
    is_provisional: bool = False
    is_partial: bool = False
    days_covered: int = 0
    days_in_month: int = 0


class YearlyHistoryData(BaseModel):
    region_id: str | None = None
    series: str = "harmonized"
    years: list[YearlyHistoryItem]


class YearlyHistoryEnvelope(ApiResponse[YearlyHistoryData]):
    pass


class MonthlyHistoryItem(BaseModel):
    year: int
    month: int
    year_month: str | None = None
    harmonized_value: float
    lower: float | None = None
    upper: float | None = None
    reliability: str | None = None
    value_type: str | None = None
    interval_applies_to: str | None = None
    modis_observed: float = 0.0
    modis_terra_observed: float = 0.0
    modis_aqua_observed: float = 0.0
    viirs_observed: float = 0.0
    days_covered: int = 0
    days_in_month: int = 0
    n_days_with_data: int = 0
    is_partial: bool = False
    is_partial_month: bool = False
    is_provisional: bool = False


class MonthlyHistoryData(BaseModel):
    region_id: str | None = None
    series: str = "harmonized"
    matrix: list[MonthlyHistoryItem]


class MonthlyHistoryEnvelope(ApiResponse[MonthlyHistoryData]):
    pass


class CurrentVsMedianData(BaseModel):
    region_id: str | None = None
    series: str = "harmonized"
    year: int
    month: int
    is_partial: bool
    is_provisional: bool = False
    current: float
    median: float
    q25: float
    q75: float
    n_baseline_years: int
    ratio_to_median: float | None = None
    ratio: float | None = None
    percentile: float = 50.0
    reliability: str = "high"
    value_type: str | None = None
    interval_applies_to: str | None = None
    days_covered: int | None = None
    days_in_month: int | None = None
    lower: float | None = None
    upper: float | None = None
    share_no_veg_history_pct: float = 0.0
    warning: str | None = None


class CurrentVsMedianEnvelope(ApiResponse[CurrentVsMedianData]):
    pass


def _clean_str(val: Any, default: str | None = None) -> str | None:
    if val is None or not isinstance(val, str):
        return default
    return val


def _clean_int(val: Any) -> int | None:
    if val is None or not isinstance(val, int):
        return None
    return val


@router.get("/yearly", response_model=YearlyHistoryEnvelope)
def get_yearly_history(
    region_id: str | None = Query("india", description="Region ID"),
    bbox: str | None = Query(None, description="Bounding box min_lon,min_lat,max_lon,max_lat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    series: str = Query("harmonized", pattern="^(harmonized|viirs_native|modis_native)$", description="Data series: harmonized, viirs_native, modis_native"),
) -> dict[str, Any]:
    """Return annual harmonized totals, intervals, and sensor mix wrapped in common envelope."""
    region_id = _clean_str(region_id, "india")
    series = _clean_str(series, "harmonized")
    bbox = _clean_str(bbox, None)

    area_type, cells, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon
    )

    params: list[Any] = []
    if cells is not None:
        if len(cells) == 0:
            y_data = YearlyHistoryData(region_id=region_id, series=series, years=[])
            meta = make_meta(series=series, reliability="insufficient", warnings=["Area contains no valid grid cells."])
            return {"data": y_data, "meta": meta}
        from_clause = "FROM harmonized_cell_day h JOIN (SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON h.h3_cell = c.h3_cell"
        params.append(cells)
    else:
        from_clause = "FROM harmonized_cell_day h"

    # Preliminary expected count to evaluate small area fallback
    count_query = f"SELECT COALESCE(SUM(h.viirs_observed), SUM(h.harmonized_value), 0.0) {from_clause}"
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
        series_clause = "h.acq_date >= '2012-01-01'"
    elif eff_series == "modis_native":
        val_expr = "h.modis_observed"
        series_clause = "1=1"
    else:  # harmonized
        val_expr = "h.harmonized_value"
        series_clause = "1=1"

    # Inspect columns
    try:
        cols = {c[0].lower() for c in repo.con.execute("DESCRIBE harmonized_cell_day").fetchall()}
    except Exception:
        cols = set()

    clauses = [series_clause]
    if "static_masked" in cols:
        clauses.append("COALESCE(h.static_masked, false) = false")
    if "is_valid" in cols:
        clauses.append("COALESCE(h.is_valid, true) = true")

    where_clause = "WHERE " + " AND ".join(clauses)

    query = f"""
        SELECT
            EXTRACT(year FROM h.acq_date)::INTEGER AS yr,
            ROUND(SUM({val_expr}), 2) AS harmonized_value,
            ROUND(SUM(h.modis_observed), 2) AS modis_observed,
            ROUND(SUM(h.viirs_observed), 2) AS viirs_observed,
            COUNT(DISTINCT h.acq_date) AS days_covered,
            BOOL_OR(h.is_provisional) AS is_provisional
        {from_clause}
        {where_clause}
        GROUP BY yr
        ORDER BY yr ASC
    """

    years_list = []
    is_any_prov = False
    try:
        df = repo.con.execute(query, params).df() if params else repo.con.execute(query).df()
        if not df.empty:
            for _, r in df.iterrows():
                yr = int(r["yr"])
                m_obs = float(r["modis_observed"]) if r["modis_observed"] is not None else 0.0
                v_obs = float(r["viirs_observed"]) if r["viirs_observed"] is not None else 0.0
                harm_val = float(r["harmonized_value"])
                prov = bool(r.get("is_provisional", False))
                if prov:
                    is_any_prov = True

                days_cov = int(r.get("days_covered", 0))
                import calendar as pycalendar
                days_in_yr = 366 if pycalendar.isleap(yr) else 365
                is_part = (yr == 2026 or yr == 2000 or days_cov < days_in_yr)

                sensor_mix = []
                if m_obs > 0:
                    sensor_mix.append("MODIS")
                if v_obs > 0:
                    sensor_mix.append("VIIRS")
                if not sensor_mix:
                    sensor_mix = ["MODIS", "VIIRS"] if yr >= 2012 else ["MODIS"]

                # Interval semantics (Task 13)
                if eff_series == "harmonized":
                    if yr >= 2012:
                        # Direct observation in VIIRS era; bridge uncertainty applied to 2022 and 2026
                        if yr in (2022, 2026):
                            l_val = round(max(0.0, harm_val * (1.0 - 0.0184)), 2)
                            u_val = round(harm_val * (1.0 + 0.0184), 2)
                        else:
                            l_val = harm_val
                            u_val = harm_val
                    else:
                        # Pre-2012 conversion interval
                        if reliability in ("insufficient", "low"):
                            # Small-area fallback: return native MODIS
                            harm_val = round(m_obs, 2)
                            l_val = harm_val
                            u_val = harm_val
                        elif rel_l is not None and rel_u is not None:
                            l_val = round(max(0.0, harm_val * (1.0 - rel_l)), 2)
                            u_val = round(harm_val * (1.0 + rel_u), 2)
                        else:
                            l_val = harm_val
                            u_val = harm_val
                elif eff_series == "viirs_native":
                    if yr in (2022, 2026):
                        l_val = round(max(0.0, harm_val * (1.0 - 0.0184)), 2)
                        u_val = round(harm_val * (1.0 + 0.0184), 2)
                    else:
                        l_val = harm_val
                        u_val = harm_val
                else:  # modis_native
                    l_val = harm_val
                    u_val = harm_val

                years_list.append(
                    YearlyHistoryItem(
                        year=yr,
                        harmonized_value=harm_val,
                        lower=l_val,
                        upper=u_val,
                        modis_observed=m_obs,
                        viirs_observed=v_obs,
                        sensor_mix=sensor_mix,
                        is_provisional=prov,
                        is_partial=is_part,
                        days_covered=days_cov,
                        days_in_month=0,
                    )
                )
    except Exception:
        pass

    y_data = YearlyHistoryData(
        region_id=region_id if not is_drawn_area else None,
        series=eff_series,
        years=years_list,
    )
    meta = make_meta(
        series=eff_series,
        method="stratified_ratio" if eff_series == "harmonized" else "identity",
        value_type="composite" if eff_series == "harmonized" else "observed",
        interval_applies_to="pre_2012_conversion_and_bridges" if eff_series == "harmonized" else "none",
        is_provisional=is_any_prov,
        reliability=reliability,
        warnings=warnings,
    )
    return {"data": y_data, "meta": meta}


@router.get("/monthly", response_model=MonthlyHistoryEnvelope)
def get_monthly_history(
    region_id: str | None = Query("india", description="Region ID"),
    bbox: str | None = Query(None, description="Bounding box min_lon,min_lat,max_lon,max_lat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    series: str = Query("harmonized", pattern="^(harmonized|viirs_native|modis_native)$", description="Data series: harmonized, viirs_native, modis_native"),
) -> dict[str, Any]:
    """Return complete Year x Month matrix of harmonized activity wrapped in common envelope."""
    region_id = _clean_str(region_id, "india")
    series = _clean_str(series, "harmonized")
    bbox = _clean_str(bbox, None)

    area_type, cells, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon
    )

    if cells is not None and len(cells) == 0:
        m_data = MonthlyHistoryData(region_id=region_id, series=series, matrix=[])
        meta = make_meta(series=series, reliability="insufficient", warnings=["Area contains no valid grid cells."])
        return {"data": m_data, "meta": meta}

    # Preliminary df to check expected monthly count
    df_pre = aggregate_area_monthly(cells=cells, series=series, con=repo.con)
    mean_count = float(df_pre["harmonized_value"].mean()) if not df_pre.empty else 0.0

    eff_series, reliability, rel_l, rel_u, warnings = evaluate_series_and_uncertainty(
        expected_count=mean_count,
        is_drawn_area=is_drawn_area,
        requested_series=series,
    )

    # Re-aggregate if series defaulted to viirs_native
    if eff_series != series:
        df = aggregate_area_monthly(cells=cells, series=eff_series, con=repo.con)
    else:
        df = df_pre

    matrix = []
    is_any_prov = False
    if not df.empty:
        for _, r in df.iterrows():
            harm_val = float(r["harmonized_value"])
            is_part = bool(r.get("is_partial", r.get("is_partial_month", False)))
            prov = bool(r.get("is_provisional", False))
            if prov:
                is_any_prov = True

            l_val = float(r["lower"]) if pd.notna(r.get("lower")) and r.get("lower") is not None else None
            u_val = float(r["upper"]) if pd.notna(r.get("upper")) and r.get("upper") is not None else None

            days_cov = int(r.get("days_covered", r.get("n_days_with_data", 0)))
            days_in_m = int(r.get("days_in_month", 0))

            matrix.append(
                MonthlyHistoryItem(
                    year=int(r["year"]),
                    month=int(r["month"]),
                    year_month=str(r.get("year_month", "")),
                    harmonized_value=harm_val,
                    lower=l_val,
                    upper=u_val,
                    reliability=str(r.get("reliability", reliability)),
                    value_type=str(r.get("value_type", "observed")),
                    interval_applies_to=str(r.get("interval_applies_to", "none")),
                    modis_observed=float(r.get("modis_observed", 0.0)),
                    modis_terra_observed=float(r.get("modis_terra_observed", 0.0)),
                    modis_aqua_observed=float(r.get("modis_aqua_observed", 0.0)),
                    viirs_observed=float(r.get("viirs_observed", 0.0)),
                    days_covered=days_cov,
                    days_in_month=days_in_m,
                    n_days_with_data=days_cov,
                    is_partial=is_part,
                    is_partial_month=is_part,
                    is_provisional=prov,
                )
            )

    m_data = MonthlyHistoryData(
        region_id=region_id if not is_drawn_area else None,
        series=eff_series,
        matrix=matrix,
    )
    meta = make_meta(
        series=eff_series,
        method="stratified_ratio" if eff_series == "harmonized" else "identity",
        value_type="composite" if eff_series == "harmonized" else "observed",
        interval_applies_to="pre_2012_conversion_and_bridges" if eff_series == "harmonized" else "none",
        is_provisional=is_any_prov,
        reliability=reliability,
        warnings=warnings,
    )
    return {"data": m_data, "meta": meta}


@router.get("/current-vs-median", response_model=CurrentVsMedianEnvelope)
def get_current_vs_median(
    region_id: str | None = Query("india", description="Region ID"),
    bbox: str | None = Query(None, description="Bounding box min_lon,min_lat,max_lon,max_lat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    series: str = Query("harmonized", pattern="^(harmonized|viirs_native|modis_native)$", description="Data series: harmonized, viirs_native, modis_native"),
    year: int | None = Query(None, description="Target year (default: latest year)"),
    month: int | None = Query(None, description="Target month (default: latest month)"),
) -> dict[str, Any]:
    """Compare selected or current month against historical baseline median wrapped in common envelope."""
    region_id = _clean_str(region_id, "india")
    series = _clean_str(series, "harmonized")
    bbox = _clean_str(bbox, None)
    year = _clean_int(year)
    month = _clean_int(month)

    area_type, cells, is_drawn_area, bbox_tuple = resolve_api_area(
        region_id=region_id, bbox=bbox, polygon=polygon
    )

    res = compute_current_vs_median(
        cells=cells,
        series=series,
        target_year=year,
        target_month=month,
        con=repo.con,
    )

    cur_val = res["current"]
    eff_series, reliability, rel_l, rel_u, warnings = evaluate_series_and_uncertainty(
        expected_count=cur_val,
        is_drawn_area=is_drawn_area,
        requested_series=series,
    )

    if eff_series != series:
        res = compute_current_vs_median(
            cells=cells,
            series=eff_series,
            target_year=year,
            target_month=month,
            con=repo.con,
        )

    all_warnings = []
    if "warnings" in res and res["warnings"]:
        for w in res["warnings"]:
            if w not in all_warnings:
                all_warnings.append(w)
    elif res.get("warning"):
        all_warnings.append(str(res["warning"]))

    for w in warnings:
        if w not in all_warnings:
            all_warnings.append(w)

    final_reliability = res.get("reliability") or reliability
    if res.get("reliability") == "low":
        final_reliability = "low"

    cvm_data = CurrentVsMedianData(
        region_id=region_id if not is_drawn_area else None,
        series=eff_series,
        year=res["year"],
        month=res["month"],
        is_partial=res["is_partial"],
        is_provisional=res["is_provisional"],
        current=res["current"],
        median=res["median"],
        q25=res["q25"],
        q75=res["q75"],
        n_baseline_years=res["n_baseline_years"],
        ratio_to_median=res["ratio"],
        ratio=res["ratio"],
        percentile=res["percentile"],
        reliability=final_reliability,
        value_type=res.get("value_type", "observed"),
        interval_applies_to=res.get("interval_applies_to", "none"),
        days_covered=res.get("days_covered"),
        days_in_month=res.get("days_in_month"),
        lower=res["lower"],
        upper=res["upper"],
        share_no_veg_history_pct=res.get("share_no_veg_history_pct", 0.0),
        warning=all_warnings[0] if all_warnings else None,
    )

    meta = make_meta(
        series=eff_series,
        method="stratified_ratio" if eff_series == "harmonized" else "identity",
        value_type=res.get("value_type", "observed"),
        interval_applies_to=res.get("interval_applies_to", "none"),
        is_provisional=res["is_provisional"],
        reliability=final_reliability,
        warnings=all_warnings,
    )
    return {"data": cvm_data, "meta": meta}
