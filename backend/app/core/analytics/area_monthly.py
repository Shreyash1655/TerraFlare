"""Area monthly activity aggregation, historical baselines, and current-vs-median analytics.

Supports:
- H3 cell sets from region_id, bbox, or polygon via grid helpers
- Series selection: 'harmonized' (default), 'viirs_native', 'modis_native'
- Single continuous VIIRS reference (S-NPP -> NOAA-20 -> NOAA-21)
- Dynamic provisional flags from manifest stream boundaries
- Exclusion of invalid and static_masked rows
- Apples-to-apples partial-month day matching (e.g. Nov 1-9 vs baseline Nov 1-9)
- Size-dependent uncertainty intervals and reliability ratings via interval_for
- Pre-computation of configured regions into a mart and on-the-fly computation for drawn areas
"""

from __future__ import annotations

import calendar
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.core.harmonization.uncertainty import interval_for
from app.core.spatial.grid import bbox_to_cells, polygon_to_cells
from app.core.storage.parquet_io import sync_duckdb_views
from app.settings import settings
from app.shared.regions import load_regions

logger = logging.getLogger("terraflare.analytics")


@dataclass
class BaselineStats:
    month: int
    median: float
    q25: float
    q75: float
    n_years: int
    baseline_period: str


_ARCHIVE_VEG_CELLS: set[str] | None = None


def _get_archive_veg_cells(connection: duckdb.DuckDBPyConnection, base_data_dir: Path) -> set[str]:
    global _ARCHIVE_VEG_CELLS
    if _ARCHIVE_VEG_CELLS is not None:
        return _ARCHIVE_VEG_CELLS
    try:
        mart_path = base_data_dir / "marts" / "cell_day_activity.parquet"
        if mart_path.exists():
            rows = connection.execute(f"SELECT DISTINCT h3_cell FROM '{mart_path.as_posix()}' WHERE date < '2026-08-01'").fetchall()
            _ARCHIVE_VEG_CELLS = {r[0] for r in rows if r[0]}
            return _ARCHIVE_VEG_CELLS
        rows = connection.execute("SELECT DISTINCT h3_cell FROM obs_clean WHERE acq_date < '2026-08-01' AND fire_type = '0'").fetchall()
        _ARCHIVE_VEG_CELLS = {r[0] for r in rows if r[0]}
    except Exception as exc:
        logger.debug(f"Could not load veg cells: {exc}")
        _ARCHIVE_VEG_CELLS = set()
    return _ARCHIVE_VEG_CELLS


def get_manifest_boundaries(data_dir: Path | None = None) -> dict[str, Any]:
    """Read stream boundaries from manifest.json."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    manifest_paths = [
        base_data_dir / "manifest.json",
        base_data_dir.parent / "manifest.json",
        Path("data/manifest.json"),
        Path("data/slice_2019_2022/manifest.json"),
    ]
    for p in manifest_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    boundaries = data.get("stream_boundaries", {})
                    if boundaries:
                        return boundaries
            except Exception:
                pass
    return {
        "modis_c61": {"sp_end_date": "2026-08-31", "nrt_start_date": "2026-09-01"},
        "viirs_snpp": {"sp_end_date": "2026-07-31", "nrt_start_date": "2026-08-01"},
        "viirs_noaa20": {"sp_end_date": "2026-07-31", "nrt_start_date": "2026-08-01"},
        "viirs_noaa21": {"sp_end_date": "2026-07-31", "nrt_start_date": "2026-08-01"},
    }


def resolve_area_cells(
    region_id: str | None = None,
    bbox: str | list[float] | None = None,
    polygon: dict[str, Any] | list | None = None,
    h3_res: int = 6,
) -> tuple[str, list[str] | None]:
    """Resolve area specification to an area type and set of H3 cell IDs.

    Returns:
        (area_type, cells_list_or_none)
        If full country (region_id='india' or 'all') with no bbox/polygon, cells is None.
    """
    if polygon:
        cells = list(polygon_to_cells(polygon, resolution=h3_res))
        return "polygon", cells

    if bbox:
        if isinstance(bbox, str):
            parts = [float(x.strip()) for x in bbox.split(",")]
            bbox_tuple = (parts[0], parts[1], parts[2], parts[3])
        else:
            bbox_tuple = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
        cells = list(bbox_to_cells(bbox_tuple, resolution=h3_res))
        return "bbox", cells

    if region_id and region_id.lower() not in ("india", "all"):
        regions = load_regions()
        if region_id in regions:
            cells = list(bbox_to_cells(regions[region_id].bbox, resolution=h3_res))
            return "region", cells

    return "country", None


# In-memory query result cache to guarantee sub-2-second warm serving latency (Task 11)
_AREA_MONTHLY_CACHE: dict[tuple[Any, ...], pd.DataFrame] = {}
_CVM_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _get_table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    """Inspect available column names in a DuckDB view/table."""
    try:
        cols = con.execute(f"DESCRIBE {table_name}").fetchall()
        return {c[0].lower() for c in cols}
    except Exception:
        return set()


def aggregate_area_monthly(
    cells: list[str] | None = None,
    series: str = "harmonized",
    data_dir: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> pd.DataFrame:
    """Compute monthly aggregation from harmonized_cell_day for an H3 cell set.

    Per month returns:
        - year, month, year_month
        - harmonized_value, lower, upper, reliability
        - modis_observed, modis_terra_observed, modis_aqua_observed, viirs_observed
        - n_days_with_data
        - is_partial_month
        - is_provisional
    """
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir

    if con is None:
        cache_key = (
            tuple(sorted(cells)) if cells else None,
            series,
            str(base_data_dir),
        )
        if cache_key in _AREA_MONTHLY_CACHE:
            return _AREA_MONTHLY_CACHE[cache_key].copy()

    connection = con or sync_duckdb_views(base_data_dir, read_only=True)

    avail_cols = _get_table_columns(connection, "harmonized_cell_day")

    # Determine global min and max dates for partial month detection
    try:
        min_max_row = connection.execute(
            "SELECT MIN(acq_date), MAX(acq_date) FROM harmonized_cell_day"
        ).fetchone()
        global_min_date = min_max_row[0] if min_max_row else None
        global_max_date = min_max_row[1] if min_max_row else None
    except Exception:
        global_min_date, global_max_date = None, None

    # Series expression
    if series == "viirs_native":
        val_expr = "h.viirs_observed"
        series_clause = "h.acq_date >= '2012-01-01'"
    elif series == "modis_native":
        val_expr = "h.modis_observed"
        series_clause = "1=1"
    else:  # harmonized
        val_expr = "h.harmonized_value"
        series_clause = "1=1"

    clauses = [series_clause]
    if "static_masked" in avail_cols:
        clauses.append("COALESCE(h.static_masked, false) = false")
    if "is_valid" in avail_cols:
        clauses.append("COALESCE(h.is_valid, true) = true")

    where_clause = "WHERE " + " AND ".join(clauses)

    prov_col = "BOOL_OR(h.is_provisional)" if "is_provisional" in avail_cols else "false"

    # Area cell filtering via unnest
    params: list[Any] = []
    if cells is not None:
        if len(cells) == 0:
            return pd.DataFrame(columns=[
                "year", "month", "year_month", "value_type", "interval_applies_to",
                "harmonized_value", "lower", "upper",
                "reliability", "modis_observed", "modis_terra_observed",
                "modis_aqua_observed", "viirs_observed", "days_covered", "days_in_month",
                "n_days_with_data", "is_partial", "is_partial_month", "is_provisional",
            ])
        from_clause = "FROM harmonized_cell_day h JOIN (SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON h.h3_cell = c.h3_cell"
        params.append(cells)
    else:
        from_clause = "FROM harmonized_cell_day h"

    query = f"""
        SELECT
            EXTRACT(year FROM h.acq_date)::INTEGER AS yr,
            EXTRACT(month FROM h.acq_date)::INTEGER AS mo,
            strftime(h.acq_date, '%Y-%m') AS year_month,
            ROUND(SUM({val_expr}), 4) AS harmonized_value,
            ROUND(SUM(h.modis_observed), 4) AS modis_observed,
            ROUND(SUM(h.modis_terra_observed), 4) AS modis_terra_observed,
            ROUND(SUM(h.modis_aqua_observed), 4) AS modis_aqua_observed,
            ROUND(SUM(h.viirs_observed), 4) AS viirs_observed,
            COUNT(DISTINCT h.acq_date) AS n_days_with_data,
            MIN(h.acq_date) AS min_acq_date,
            MAX(h.acq_date) AS max_acq_date,
            {prov_col} AS is_provisional
        {from_clause}
        {where_clause}
        GROUP BY yr, mo, year_month
        ORDER BY yr ASC, mo ASC
    """

    try:
        df = connection.execute(query, params).df() if params else connection.execute(query).df()
    except Exception as exc:
        logger.warning(f"Error querying monthly activity: {exc}")
        df = pd.DataFrame()

    if df.empty:
        return pd.DataFrame(columns=[
            "year", "month", "year_month", "value_type", "interval_applies_to",
            "harmonized_value", "lower", "upper",
            "reliability", "modis_observed", "modis_terra_observed",
            "modis_aqua_observed", "viirs_observed", "days_covered", "days_in_month",
            "n_days_with_data", "is_partial", "is_partial_month", "is_provisional",
        ])

    boundaries = get_manifest_boundaries(base_data_dir)
    nrt_start_viirs = boundaries.get("viirs_snpp", {}).get("nrt_start_date", "2026-08-01")
    nrt_start_modis = boundaries.get("modis_c61", {}).get("nrt_start_date", "2026-09-01")

    records = []
    for _, r in df.iterrows():
        yr = int(r["yr"])
        mo = int(r["mo"])
        ym = str(r["year_month"])
        harm_val = float(r["harmonized_value"]) if pd.notna(r["harmonized_value"]) else 0.0
        m_obs = float(r["modis_observed"]) if pd.notna(r["modis_observed"]) else 0.0
        mt_obs = float(r["modis_terra_observed"]) if pd.notna(r["modis_terra_observed"]) else 0.0
        ma_obs = float(r["modis_aqua_observed"]) if pd.notna(r["modis_aqua_observed"]) else 0.0
        v_obs = float(r["viirs_observed"]) if pd.notna(r["viirs_observed"]) else 0.0
        n_days = int(r["n_days_with_data"])
        max_d = r["max_acq_date"]
        min_d = r["min_acq_date"]

        days_in_month = calendar.monthrange(yr, mo)[1]

        # Partial month logic
        is_partial = False
        if global_max_date and max_d:
            max_d_ts = pd.to_datetime(max_d).date()
            g_max_ts = pd.to_datetime(global_max_date).date()
            if max_d_ts >= g_max_ts and max_d_ts.day < days_in_month:
                is_partial = True

        if global_min_date and min_d:
            min_d_ts = pd.to_datetime(min_d).date()
            g_min_ts = pd.to_datetime(global_min_date).date()
            if min_d_ts <= g_min_ts and min_d_ts.day > 1:
                is_partial = True

        # Provisional logic from manifest and data flag
        if series == "modis_native":
            is_prov = ym >= str(nrt_start_modis)[:7]
        else:
            is_prov = ym >= str(nrt_start_viirs)[:7]

        if bool(r["is_provisional"]):
            is_prov = True

        # Bounds, reliability, and value_type semantics (Task 13)
        bridge_months = {"2022-07", "2022-08", "2026-11"}
        if series == "harmonized":
            if ym >= "2012-01":
                value_type = "observed"
                if ym in bridge_months:
                    lower = round(max(0.0, harm_val * (1.0 - 0.0184)), 2)
                    upper = round(harm_val * (1.0 + 0.0184), 2)
                    reliability = "observed"
                    interval_applies_to = "bridge_uncertainty"
                else:
                    lower = round(harm_val, 2)
                    upper = round(harm_val, 2)
                    reliability = "observed"
                    interval_applies_to = "none"
            else:
                # Pre-VIIRS era (date < 2012-01-20): conversion interval from backward holdouts
                rel_l, rel_u, reliability = interval_for(harm_val)
                if reliability in ("insufficient", "low"):
                    # Small-area fallback: keep 2012+ observed series and return modis_native for pre-2012
                    harm_val = round(m_obs, 2)
                    lower = harm_val
                    upper = harm_val
                    reliability = "low"
                    value_type = "modis_native"
                    interval_applies_to = "none"
                else:
                    value_type = "estimated, extrapolated"
                    interval_applies_to = "conversion_model"
                    if rel_l is not None and rel_u is not None:
                        lower = round(max(0.0, harm_val * (1.0 - rel_l)), 2)
                        upper = round(harm_val * (1.0 + rel_u), 2)
                    else:
                        lower, upper = None, None
                        reliability = "insufficient"
        elif series == "viirs_native":
            value_type = "observed"
            if ym in bridge_months:
                lower = round(max(0.0, harm_val * (1.0 - 0.0184)), 2)
                upper = round(harm_val * (1.0 + 0.0184), 2)
                reliability = "observed"
                interval_applies_to = "bridge_uncertainty"
            else:
                lower = round(harm_val, 2)
                upper = round(harm_val, 2)
                reliability = "observed"
                interval_applies_to = "none"
        else:  # modis_native
            value_type = "observed"
            lower = round(harm_val, 2)
            upper = round(harm_val, 2)
            reliability = "observed"
            interval_applies_to = "none"

        records.append({
            "year": yr,
            "month": mo,
            "year_month": ym,
            "value_type": value_type,
            "interval_applies_to": interval_applies_to,
            "harmonized_value": round(harm_val, 2),
            "lower": lower,
            "upper": upper,
            "reliability": reliability,
            "modis_observed": round(m_obs, 2),
            "modis_terra_observed": round(mt_obs, 2),
            "modis_aqua_observed": round(ma_obs, 2),
            "viirs_observed": round(v_obs, 2),
            "days_covered": n_days,
            "days_in_month": days_in_month,
            "n_days_with_data": n_days,
            "is_partial": is_partial,
            "is_partial_month": is_partial,
            "is_provisional": is_prov,
        })

    res_df = pd.DataFrame(records)
    if con is None:
        if len(_AREA_MONTHLY_CACHE) > 256:
            _AREA_MONTHLY_CACHE.clear()
        _AREA_MONTHLY_CACHE[cache_key] = res_df.copy()
    return res_df


def compute_area_baselines(
    monthly_df: pd.DataFrame | None = None,
    region_id: str | None = None,
    series: str = "harmonized",
    data_dir: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> dict[int, BaselineStats]:
    """Compute monthly baselines (median, q25, q75, n_years, baseline_period).

    Rule (Task 9):
    Uses complete non-provisional months only.
    Reads pre-computed mart if present for configured region; otherwise computes on the fly.
    """
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    mart_file = base_data_dir / "marts" / "baselines.parquet"

    # Pre-computed mart check
    if region_id and mart_file.exists():
        try:
            df_mart = pd.read_parquet(mart_file)
            matched = df_mart[(df_mart["region_id"] == region_id) & (df_mart["series"] == series)]
            if not matched.empty:
                baselines: dict[int, BaselineStats] = {}
                for _, r in matched.iterrows():
                    mo = int(r["month"])
                    baselines[mo] = BaselineStats(
                        month=mo,
                        median=float(r["median"]),
                        q25=float(r["q25"]),
                        q75=float(r["q75"]),
                        n_years=int(r["n_years"]),
                        baseline_period=str(r["baseline_period"]),
                    )
                return baselines
        except Exception as exc:
            logger.warning(f"Failed loading baselines mart: {exc}")

    if monthly_df is None or monthly_df.empty:
        if region_id:
            regions = load_regions()
            cells = list(bbox_to_cells(regions[region_id].bbox, resolution=6)) if region_id not in ("india", "all") and region_id in regions else None
            monthly_df = aggregate_area_monthly(cells=cells, series=series, data_dir=base_data_dir, con=con)
        else:
            return {}

    if monthly_df is None or monthly_df.empty:
        return {}

    # Complete non-provisional months only
    valid = monthly_df[
        (~monthly_df["is_partial_month"]) & (~monthly_df["is_provisional"])
    ].copy()

    if valid.empty:
        return {}

    min_yr = int(valid["year"].min())
    max_yr = int(valid["year"].max())
    baseline_period = f"{min_yr}-{max_yr}"

    baselines = {}
    for mo in range(1, 13):
        m_rows = valid[valid["month"] == mo]
        if m_rows.empty:
            continue
        vals = m_rows["harmonized_value"].astype(float).to_numpy()
        med = float(np.median(vals))
        q25 = float(np.percentile(vals, 25))
        q75 = float(np.percentile(vals, 75))
        baselines[mo] = BaselineStats(
            month=mo,
            median=round(med, 2),
            q25=round(q25, 2),
            q75=round(q75, 2),
            n_years=len(vals),
            baseline_period=baseline_period,
        )

    return baselines


def compute_current_vs_median(
    cells: list[str] | None = None,
    series: str = "harmonized",
    target_year: int | None = None,
    target_month: int | None = None,
    data_dir: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> dict[str, Any]:
    """Compare latest/target month against historical baseline for that calendar month.

    Rule (Task 9):
    For a partial month, compare the EXACT SAME DAYS only across baseline years.
    Returns:
        current, median, q25, q75, ratio, percentile, n_baseline_years,
        is_partial, is_provisional, reliability, lower, upper, warning
    """
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir

    if con is None:
        cvm_cache_key = (
            tuple(sorted(cells)) if cells else None,
            series,
            target_year,
            target_month,
            str(base_data_dir),
        )
        if cvm_cache_key in _CVM_CACHE:
            return dict(_CVM_CACHE[cvm_cache_key])

    connection = con or sync_duckdb_views(base_data_dir, read_only=True)

    avail_cols = _get_table_columns(connection, "harmonized_cell_day")

    # Series expression
    if series == "viirs_native":
        val_expr = "h.viirs_observed"
        series_clause = "h.acq_date >= '2012-01-01'"
    elif series == "modis_native":
        val_expr = "h.modis_observed"
        series_clause = "1=1"
    else:  # harmonized
        val_expr = "h.harmonized_value"
        series_clause = "1=1"

    clauses = [series_clause]
    if "static_masked" in avail_cols:
        clauses.append("COALESCE(h.static_masked, false) = false")
    if "is_valid" in avail_cols:
        clauses.append("COALESCE(h.is_valid, true) = true")

    base_where = " AND ".join(clauses)

    params: list[Any] = []
    if cells is not None:
        if len(cells) == 0:
            return {
                "year": target_year or 2026,
                "month": target_month or 11,
                "current": 0.0,
                "median": 0.0,
                "q25": 0.0,
                "q75": 0.0,
                "ratio": None,
                "percentile": 0.0,
                "n_baseline_years": 0,
                "is_partial": False,
                "is_provisional": False,
                "reliability": "insufficient",
                "lower": None,
                "upper": None,
                "warning": "No observation data found for the selected area.",
            }
        from_clause = "FROM harmonized_cell_day h JOIN (SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON h.h3_cell = c.h3_cell"
        params.append(cells)
    else:
        from_clause = "FROM harmonized_cell_day h"

    # Find latest year and month if not provided
    if target_year is None or target_month is None:
        latest_sql = f"""
            SELECT 
                EXTRACT(year FROM h.acq_date)::INTEGER AS yr,
                EXTRACT(month FROM h.acq_date)::INTEGER AS mo,
                MAX(h.acq_date) AS max_d
            {from_clause}
            WHERE {base_where}
            GROUP BY yr, mo
            ORDER BY yr DESC, mo DESC
            LIMIT 1
        """
        latest_row = connection.execute(latest_sql, params).fetchone() if params else connection.execute(latest_sql).fetchone()

        if not latest_row:
            return {
                "year": target_year or 2026,
                "month": target_month or 11,
                "current": 0.0,
                "median": 0.0,
                "q25": 0.0,
                "q75": 0.0,
                "ratio": None,
                "percentile": 0.0,
                "n_baseline_years": 0,
                "is_partial": False,
                "is_provisional": False,
                "reliability": "insufficient",
                "lower": None,
                "upper": None,
                "warning": "No observation data found for the selected area.",
            }
        t_year = int(latest_row[0])
        t_month = int(latest_row[1])
        t_max_date = latest_row[2]
    else:
        t_year = target_year
        t_month = target_month
        max_d_sql = f"""
            SELECT MAX(h.acq_date)
            {from_clause}
            WHERE {base_where}
              AND EXTRACT(year FROM h.acq_date) = {t_year}
              AND EXTRACT(month FROM h.acq_date) = {t_month}
        """
        max_d_res = connection.execute(max_d_sql, params).fetchone() if params else connection.execute(max_d_sql).fetchone()
        t_max_date = max_d_res[0] if max_d_res else None

    # Check partial status of target month
    days_in_month = calendar.monthrange(t_year, t_month)[1]
    if t_max_date is not None:
        max_day = pd.to_datetime(t_max_date).day
        is_partial = max_day < days_in_month
    else:
        max_day = days_in_month
        is_partial = False

    # Target month sum
    day_filter = f"AND EXTRACT(day FROM h.acq_date) <= {max_day}" if is_partial else ""

    prov_col = "BOOL_OR(h.is_provisional)" if "is_provisional" in avail_cols else "false"

    cur_sql = f"""
        SELECT 
            ROUND(SUM({val_expr}), 2) AS current_val,
            {prov_col} AS is_prov
        {from_clause}
        WHERE {base_where}
          AND EXTRACT(year FROM h.acq_date) = {t_year}
          AND EXTRACT(month FROM h.acq_date) = {t_month}
          {day_filter}
    """
    current_res = connection.execute(cur_sql, params).fetchone() if params else connection.execute(cur_sql).fetchone()

    current_val = float(current_res[0]) if current_res and current_res[0] is not None else 0.0
    is_prov = bool(current_res[1]) if current_res and current_res[1] is not None else False

    # Manifest boundaries check for provisional flag
    boundaries = get_manifest_boundaries(base_data_dir)
    nrt_start = (
        boundaries.get("modis_c61", {}).get("nrt_start_date", "2026-09-01")
        if series == "modis_native"
        else boundaries.get("viirs_snpp", {}).get("nrt_start_date", "2026-08-01")
    )
    target_ym = f"{t_year:04d}-{t_month:02d}"
    if target_ym >= str(nrt_start)[:7]:
        is_prov = True

    # Baseline query: compare against complete non-provisional baseline years
    # Rule (Task 9): For a partial month, compare the EXACT SAME DAYS only!
    start_baseline_yr = 2012 if series in ("harmonized", "viirs_native") else 2001
    baseline_query = f"""
        SELECT 
            EXTRACT(year FROM h.acq_date)::INTEGER AS yr,
            ROUND(SUM({val_expr}), 2) AS yr_sum
        {from_clause}
        WHERE {base_where}
          AND EXTRACT(month FROM h.acq_date) = {t_month}
          AND EXTRACT(year FROM h.acq_date) >= {start_baseline_yr}
          AND EXTRACT(year FROM h.acq_date) < {t_year}
          AND strftime(h.acq_date, '%Y-%m') < '{str(nrt_start)[:7]}'
          {day_filter}
        GROUP BY yr
        ORDER BY yr ASC
    """

    hist_df = connection.execute(baseline_query, params).df() if params else connection.execute(baseline_query).df()
    if not hist_df.empty:
        baseline_vals = hist_df["yr_sum"].astype(float).tolist()
    else:
        baseline_vals = []

    if baseline_vals:
        med = float(np.median(baseline_vals))
        q25 = float(np.percentile(baseline_vals, 25))
        q75 = float(np.percentile(baseline_vals, 75))
        ratio = round(current_val / med, 3) if med > 0 else None
        pctile = round(float(np.mean(np.array(baseline_vals) <= current_val) * 100.0), 1)
        n_baseline = len(baseline_vals)
    else:
        med = current_val
        q25, q75 = current_val, current_val
        ratio = 1.0 if current_val > 0 else None
        pctile = 50.0
        n_baseline = 0

    # Uncertainty & reliability rating from interval semantics (Task 13)
    bridge_months = {"2022-07", "2022-08", "2026-11"}
    if series == "harmonized":
        if t_year >= 2012:
            value_type = "observed"
            if target_ym in bridge_months:
                lower = round(max(0.0, current_val * (1.0 - 0.0184)), 2)
                upper = round(current_val * (1.0 + 0.0184), 2)
                reliability = "observed"
                interval_applies_to = "bridge_uncertainty"
            else:
                lower = round(current_val, 2)
                upper = round(current_val, 2)
                reliability = "observed"
                interval_applies_to = "none"
        else:
            rel_l, rel_u, reliability = interval_for(current_val)
            value_type = "estimated, extrapolated"
            interval_applies_to = "conversion_model"
            if rel_l is not None and rel_u is not None:
                lower = round(max(0.0, current_val * (1.0 - rel_l)), 2)
                upper = round(current_val * (1.0 + rel_u), 2)
            else:
                lower, upper = None, None
                reliability = "insufficient"
    elif series == "viirs_native":
        value_type = "observed"
        if target_ym in bridge_months:
            lower = round(max(0.0, current_val * (1.0 - 0.0184)), 2)
            upper = round(current_val * (1.0 + 0.0184), 2)
            reliability = "observed"
            interval_applies_to = "bridge_uncertainty"
        else:
            lower = round(current_val, 2)
            upper = round(current_val, 2)
            reliability = "observed"
            interval_applies_to = "none"
    else:  # modis_native
        value_type = "observed"
        lower = round(current_val, 2)
        upper = round(current_val, 2)
        reliability = "observed"
        interval_applies_to = "none"

    warnings_list: list[str] = []
    if current_val < 50 or reliability == "insufficient":
        warnings_list.append("Area is small: uncertainty intervals are wide and satellite detection intermittency is high")

    # Task 14: Provisional month low-count validation warning & reliability downgrade
    # When a month is provisional and country-level count < 5,000, add warning and set reliability 'low'
    if is_prov:
        if cells is None:
            country_count = current_val
        else:
            q_country = f"""
                SELECT ROUND(SUM({val_expr}), 2)
                FROM harmonized_cell_day h
                WHERE {base_where}
                  AND EXTRACT(year FROM h.acq_date) = {t_year}
                  AND EXTRACT(month FROM h.acq_date) = {t_month}
                  {day_filter}
            """
            c_res = connection.execute(q_country).fetchone()
            country_count = float(c_res[0]) if c_res and c_res[0] is not None else 0.0

        if country_count < 5000:
            warnings_list.append("provisional NRT vs standard-processing baseline; not validated")
            reliability = "low"

    # Check share of detections in cells with no archive vegetation history (Task 9 Addendum Point D)
    share_no_veg_pct = 0.0
    try:
        veg_set = _get_archive_veg_cells(connection, base_data_dir)
        obs_clean_cols = _get_table_columns(connection, "obs_clean")
        if veg_set and obs_clean_cols and "processing_stream" in obs_clean_cols:
            from_obs = "FROM obs_clean o"
            obs_params = []
            if cells is not None:
                from_obs = "FROM obs_clean o JOIN (SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON o.h3_cell = c.h3_cell"
                obs_params.append(cells)

            obs_day_filter = day_filter.replace("h.", "o.")
            obs_sql = f"""
                SELECT o.h3_cell
                {from_obs}
                WHERE EXTRACT(year FROM o.acq_date) = {t_year} 
                  AND EXTRACT(month FROM o.acq_date) = {t_month}
                  {obs_day_filter}
                  AND o.processing_stream = 'NRT'
            """
            nrt_cells_res = connection.execute(obs_sql, obs_params).fetchall() if obs_params else connection.execute(obs_sql).fetchall()
            if nrt_cells_res:
                tot_n = float(len(nrt_cells_res))
                with_v = float(sum(1 for r in nrt_cells_res if r[0] in veg_set))
                share_no_veg_pct = round((tot_n - with_v) * 100.0 / tot_n, 3)
    except Exception as exc:
        logger.debug(f"Could not compute no-veg history share: {exc}")

    from app.core.harmonization.uncertainty import get_size_dependent_uncertainty_config
    u_cfg = get_size_dependent_uncertainty_config()
    thresh_pct = float(u_cfg.get("static_contamination_threshold_pct", 0.20))

    if share_no_veg_pct > thresh_pct:
        warnings_list.append(f"possible_static_contamination: {share_no_veg_pct:.2f}% of detections in cells with no archive vegetation history")

    res_dict = {
        "year": t_year,
        "month": t_month,
        "current": round(current_val, 2),
        "median": round(med, 2),
        "q25": round(q25, 2),
        "q75": round(q75, 2),
        "ratio": ratio,
        "percentile": pctile,
        "n_baseline_years": n_baseline,
        "days_covered": max_day,
        "days_in_month": days_in_month,
        "is_partial": is_partial,
        "is_provisional": is_prov,
        "reliability": reliability,
        "value_type": value_type,
        "interval_applies_to": interval_applies_to,
        "lower": lower,
        "upper": upper,
        "share_no_veg_history_pct": share_no_veg_pct,
        "warning": "; ".join(warnings_list) if warnings_list else None,
        "warnings": warnings_list,
    }
    if con is None:
        if len(_CVM_CACHE) > 256:
            _CVM_CACHE.clear()
        _CVM_CACHE[cvm_cache_key] = dict(res_dict)
    return res_dict


def precompute_configured_baselines(
    data_dir: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Pre-compute baselines for configured regions into a DataFrame and optional Parquet mart."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    connection = sync_duckdb_views(base_data_dir, read_only=True)
    regions = load_regions()

    records = []
    for rid in list(regions.keys()):
        cells = list(bbox_to_cells(regions[rid].bbox, resolution=6)) if rid not in ("india", "all") else None
        for series in ["harmonized", "viirs_native", "modis_native"]:
            m_df = aggregate_area_monthly(cells=cells, series=series, data_dir=base_data_dir, con=connection)
            b_map = compute_area_baselines(monthly_df=m_df, region_id=None, series=series, data_dir=base_data_dir, con=connection)
            for mo, b in b_map.items():
                records.append({
                    "region_id": rid,
                    "series": series,
                    "month": mo,
                    "median": b.median,
                    "q25": b.q25,
                    "q75": b.q75,
                    "n_years": b.n_years,
                    "baseline_period": b.baseline_period,
                })

    df = pd.DataFrame(records)
    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_p, index=False)
        logger.info(f"Saved precomputed baselines to {out_p}")
    return df
