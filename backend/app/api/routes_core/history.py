"""Core API routes: /api/v1/history/yearly, /api/v1/history/monthly, /api/v1/history/current-vs-median."""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.storage.duckdb_repo import DuckDBRepository
from app.shared.regions import load_regions

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


class YearlyHistoryResponse(BaseModel):
    region_id: str
    years: list[YearlyHistoryItem]


class MonthlyHistoryItem(BaseModel):
    year: int
    month: int
    harmonized_value: float
    lower: float
    upper: float
    is_partial: bool = False
    is_provisional: bool = False


class MonthlyHistoryResponse(BaseModel):
    region_id: str
    matrix: list[MonthlyHistoryItem]


class CurrentVsMedianResponse(BaseModel):
    region_id: str
    year: int
    month: int
    is_partial: bool
    current: float
    median: float
    q25: float
    q75: float
    n_baseline_years: int
    ratio_to_median: float | None


@router.get("/yearly", response_model=YearlyHistoryResponse)
def get_yearly_history(
    region_id: str = Query("india", description="Region ID"),
) -> dict[str, Any]:
    """Return annual harmonized totals, intervals, and sensor mix."""
    regions = load_regions()
    if region_id not in regions:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")

    query = f"""
        SELECT
            EXTRACT(year FROM acq_date)::INTEGER AS yr,
            ROUND(SUM(harmonized_value), 2) AS harmonized_value,
            ROUND(SUM(harmonized_lower), 2) AS lower,
            ROUND(SUM(harmonized_upper), 2) AS upper,
            ROUND(SUM(modis_observed), 2) AS modis_observed,
            ROUND(SUM(viirs_observed), 2) AS viirs_observed
        FROM harmonized_cell_day
        WHERE region_id = '{region_id}'
        GROUP BY yr
        ORDER BY yr ASC
    """

    years_list = []
    try:
        df = repo.con.execute(query).df()
        if not df.empty:
            for _, r in df.iterrows():
                yr = int(r["yr"])
                m_obs = float(r["modis_observed"]) if r["modis_observed"] is not None else 0.0
                v_obs = float(r["viirs_observed"]) if r["viirs_observed"] is not None else 0.0
                harm_val = float(r["harmonized_value"])

                sensor_mix = []
                if m_obs > 0:
                    sensor_mix.append("MODIS")
                if v_obs > 0:
                    sensor_mix.append("VIIRS")
                if not sensor_mix:
                    sensor_mix = ["MODIS", "VIIRS"] if yr >= 2012 else ["MODIS"]

                years_list.append(
                    YearlyHistoryItem(
                        year=yr,
                        harmonized_value=harm_val,
                        lower=float(r["lower"]) if r["lower"] is not None else round(harm_val * 0.8, 2),
                        upper=float(r["upper"]) if r["upper"] is not None else round(harm_val * 1.2, 2),
                        modis_observed=m_obs,
                        viirs_observed=v_obs,
                        sensor_mix=sensor_mix,
                    )
                )
    except Exception:
        pass

    return {"region_id": region_id, "years": years_list}


@router.get("/monthly", response_model=MonthlyHistoryResponse)
def get_monthly_history(
    region_id: str = Query("india", description="Region ID"),
) -> dict[str, Any]:
    """Return complete Year x Month matrix of harmonized activity."""
    regions = load_regions()
    if region_id not in regions:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")

    query = f"""
        SELECT
            EXTRACT(year FROM acq_date)::INTEGER AS yr,
            EXTRACT(month FROM acq_date)::INTEGER AS mo,
            ROUND(SUM(harmonized_value), 2) AS harmonized_value,
            ROUND(SUM(harmonized_lower), 2) AS lower,
            ROUND(SUM(harmonized_upper), 2) AS upper,
            BOOL_OR(is_provisional) AS is_provisional
        FROM harmonized_cell_day
        WHERE region_id = '{region_id}'
        GROUP BY yr, mo
        ORDER BY yr ASC, mo ASC
    """

    matrix = []
    try:
        df = repo.con.execute(query).df()
        if not df.empty:
            for _, r in df.iterrows():
                val = float(r["harmonized_value"])
                matrix.append(
                    MonthlyHistoryItem(
                        year=int(r["yr"]),
                        month=int(r["mo"]),
                        harmonized_value=val,
                        lower=float(r["lower"]) if r["lower"] is not None else round(val * 0.8, 2),
                        upper=float(r["upper"]) if r["upper"] is not None else round(val * 1.2, 2),
                        is_partial=False,
                        is_provisional=bool(r["is_provisional"]) if r["is_provisional"] is not None else False,
                    )
                )
    except Exception:
        pass

    return {"region_id": region_id, "matrix": matrix}


@router.get("/current-vs-median", response_model=CurrentVsMedianResponse)
def get_current_vs_median(
    region_id: str = Query("india", description="Region ID"),
    year: int | None = Query(None, description="Target year (default: latest year)"),
    month: int | None = Query(None, description="Target month (default: latest month)"),
) -> dict[str, Any]:
    """Compare the selected or current month against historical baseline median for that calendar month."""
    regions = load_regions()
    if region_id not in regions:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")

    # Fetch monthly totals for this region
    query = f"""
        SELECT
            EXTRACT(year FROM acq_date)::INTEGER AS yr,
            EXTRACT(month FROM acq_date)::INTEGER AS mo,
            ROUND(SUM(harmonized_value), 2) AS val,
            BOOL_OR(is_provisional) AS is_provisional
        FROM harmonized_cell_day
        WHERE region_id = '{region_id}'
        GROUP BY yr, mo
        ORDER BY yr ASC, mo ASC
    """

    try:
        df = repo.con.execute(query).df()
    except Exception:
        df = None

    if df is None or df.empty:
        return {
            "region_id": region_id,
            "year": year or 2026,
            "month": month or 1,
            "is_partial": False,
            "current": 0.0,
            "median": 0.0,
            "q25": 0.0,
            "q75": 0.0,
            "n_baseline_years": 0,
            "ratio_to_median": None,
        }

    # Determine default year and month if omitted
    if year is None or month is None:
        latest = df.iloc[-1]
        target_yr = int(latest["yr"]) if year is None else year
        target_mo = int(latest["mo"]) if month is None else month
    else:
        target_yr = year
        target_mo = month

    cur_row = df[(df["yr"] == target_yr) & (df["mo"] == target_mo)]
    current_val = float(cur_row["val"].iloc[0]) if not cur_row.empty else 0.0

    # Baseline years: all other years with the same calendar month
    baseline_df = df[(df["yr"] != target_yr) & (df["mo"] == target_mo)]
    if baseline_df.empty:
        # If no other years, include current as sole data
        baseline_vals = [current_val]
    else:
        baseline_vals = baseline_df["val"].astype(float).tolist()

    n_baseline = len(baseline_vals)
    med = float(np.median(baseline_vals))
    q25 = float(np.percentile(baseline_vals, 25))
    q75 = float(np.percentile(baseline_vals, 75))
    ratio = round(current_val / med, 3) if med > 0 else None

    return {
        "region_id": region_id,
        "year": target_yr,
        "month": target_mo,
        "is_partial": False,
        "current": round(current_val, 2),
        "median": round(med, 2),
        "q25": round(q25, 2),
        "q75": round(q75, 2),
        "n_baseline_years": n_baseline,
        "ratio_to_median": ratio,
    }
