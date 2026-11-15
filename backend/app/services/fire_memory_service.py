"""Feature 2 - Fire Memory Map (recurrence classes per grid cell)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import settings
from app.utils.errors import TerraFlareError
from app.utils.response import num


# Assumption: a year with more uncovered days than this is incomplete and excluded.
MAX_MISSING_DAYS = 14

LIMITATIONS = [
    "Recurrence means detections occurred in a cell in several years, not that the same fire recurred.",
    "Persistent industrial, volcanic or gas-flare heat sources may appear as 'persistent' (no land-cover mask).",
    "Cell size and thresholds are descriptive choices, not scientific constants.",
    "Years with missing satellite coverage are excluded, never counted as zero activity.",
]

MEMORY_CLASSES = {"persistent", "emerging", "declining", "sporadic"}


def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    required = {"h3_cell", "acq_date", "harmonized_value"}
    missing = required - set(df.columns)
    if missing:
        raise TerraFlareError("invalid_data", f"Missing required columns: {sorted(missing)}", 500)

    result = df.copy()
    result["acq_date"] = pd.to_datetime(result["acq_date"], errors="coerce")
    result["harmonized_value"] = pd.to_numeric(result["harmonized_value"], errors="coerce")
    result = result.dropna(subset=["h3_cell", "acq_date", "harmonized_value"])
    result["h3_cell"] = result["h3_cell"].astype(str)
    result["acq_date"] = result["acq_date"].dt.normalize()
    return result[np.isfinite(result["harmonized_value"])]


def _complete_years(repo, df: pd.DataFrame) -> tuple[list[int], list[int]]:
    """Return (complete_years, excluded_years).

    Years listed in coverage_day are judged by covered days. Years the table
    does not list have unknown coverage, so only the edge rule applies
    (data spans 1 Jan to 31 Dec). Unknown coverage is never counted as zero.
    """
    years = sorted(int(y) for y in df["acq_date"].dt.year.unique())
    d0, d1 = df["acq_date"].min(), df["acq_date"].max()
    ok_days = None
    try:
        p = Path(repo.data_dir) / "marts" / "coverage_day.parquet"
        if p.exists():
            c = pd.read_parquet(p, columns=["acq_date", "viirs_covered", "viirs_suspect_zero"])
            c["acq_date"] = pd.to_datetime(c["acq_date"]).dt.normalize()
            ok = c["viirs_covered"].fillna(False).astype(bool) & ~c["viirs_suspect_zero"].fillna(False).astype(bool)
            ok_days = ok.groupby(c["acq_date"].dt.year).sum()
    except Exception:
        ok_days = None

    complete, excluded = [], []
    for y in years:
        n_days = 366 if pd.Timestamp(y, 12, 31).day_of_year == 366 else 365
        edge_ok = d0 <= pd.Timestamp(y, 1, 1) and d1 >= pd.Timestamp(y, 12, 31)
        if ok_days is not None and y in ok_days.index:
            good = edge_ok and int(ok_days.loc[y]) >= n_days - MAX_MISSING_DAYS
        else:  # coverage unknown for this year: edge rule only
            good = edge_ok
        (complete if good else excluded).append(y)
    return complete, excluded


def _annual_matrix(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    d = df[df["acq_date"].dt.year.isin(years)][["h3_cell", "harmonized_value", "acq_date"]].copy()
    d["year"] = d["acq_date"].dt.year
    matrix = d.groupby(["h3_cell", "year"])["harmonized_value"].sum().unstack(fill_value=0.0)
    if matrix.empty:
        return matrix
    # Cell-level 0 in a complete (covered) year = no detections in that cell.
    return matrix.reindex(columns=years, fill_value=0.0)


def _theil_sen_rows(x: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Vectorised Theil-Sen: median of pairwise slopes, per row."""
    n = len(x)
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((values[:, j] - values[:, i]) / (x[j] - x[i]))
    return np.median(np.stack(slopes, axis=1), axis=1)


def _classify_cells(matrix: pd.DataFrame, years: np.ndarray) -> pd.DataFrame:
    values = matrix.to_numpy(dtype=float)
    active = values > 0
    n_years = len(years)

    recent_window = min(settings.memory_recent_window_years, n_years - 1)
    split = n_years - recent_window

    early_values, recent_values = values[:, :split], values[:, split:]
    early_active, recent_active = active[:, :split], active[:, split:]

    early_recurrence = early_active.mean(axis=1)
    early_mean = early_values.mean(axis=1)
    recent_mean = recent_values.mean(axis=1)
    recent_active_years = recent_active.sum(axis=1)
    recurrence = active.sum(axis=1) / n_years
    overall_mean = values.mean(axis=1)

    if recent_window >= 3:
        slopes = _theil_sen_rows(years[split:].astype(float), recent_values)
    else:
        slopes = np.full(len(matrix), np.nan, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        relative_trend = slopes / overall_mean
    relative_trend = np.nan_to_num(relative_trend, nan=0.0, posinf=0.0, neginf=0.0)

    strong = settings.memory_strong_trend

    declining = (early_mean > 0) & (
        (relative_trend <= -strong) | (recent_mean <= settings.memory_drop_ratio * early_mean)
    )
    persistent = (
        (recurrence >= settings.memory_high_recurrence)
        & (np.abs(relative_trend) < strong)
        & ~declining
    )
    emerging = (
        (early_recurrence <= settings.memory_emerging_early_max)
        & (recent_active_years >= 2)
        & (relative_trend > 0)
        & ~persistent
        & ~declining
    )

    memory_class = np.select(
        [persistent, emerging, declining],
        ["persistent", "emerging", "declining"],
        default="sporadic",
    )

    has_activity = active.any(axis=1)
    first_active = np.zeros(len(matrix), dtype=int)
    last_active = np.zeros(len(matrix), dtype=int)
    if has_activity.any():
        first_idx = np.argmax(active[has_activity], axis=1)
        last_idx = n_years - 1 - np.argmax(active[has_activity, ::-1], axis=1)
        first_active[has_activity] = years[first_idx]
        last_active[has_activity] = years[last_idx]

    return pd.DataFrame(
        {
            "h3_cell": matrix.index,
            "recurrence": recurrence,
            "years_active": active.sum(axis=1),
            "years_in_range": n_years,
            "trend_slope": slopes,
            "memory_class": memory_class,
            "total_activity": values.sum(axis=1),
            "first_active_year": first_active,
            "last_active_year": last_active,
        }
    )


def compute_cells(repo, region_id, memory_class, min_activity, limit) -> dict:
    df = _prepare_data(repo.get_harmonized(region_id))
    if df.empty:
        raise TerraFlareError("no_data", "No valid harmonized data for this region", 404)

    if memory_class is not None and memory_class not in MEMORY_CLASSES:
        raise TerraFlareError("invalid_memory_class", f"Unknown memory class: {memory_class}", 400)
    if limit < 1:
        raise TerraFlareError("invalid_limit", "Limit must be at least 1", 400)
    if min_activity < 0:
        raise TerraFlareError("invalid_min_activity", "Minimum activity cannot be negative", 400)

    complete, excluded = _complete_years(repo, df)
    if len(complete) < settings.memory_min_years:
        raise TerraFlareError(
            "insufficient_years",
            f"Fire memory needs at least {settings.memory_min_years} complete years; "
            f"found {len(complete)} (excluded as incomplete: {excluded or 'none'}).",
            422,
        )

    matrix = _annual_matrix(df, complete)
    years = np.array(matrix.columns, dtype=int)
    n_years = len(years)
    recent_window = min(settings.memory_recent_window_years, n_years - 1)

    matrix = matrix[matrix.sum(axis=1) >= min_activity]

    year_range = [int(years[0]), int(years[-1])]
    recent_range = [int(years[-recent_window]), int(years[-1])]
    excl_note = (
        f"Incomplete years excluded (missing satellite coverage, not treated as zero): {excluded}."
        if excluded else None
    )

    if matrix.empty:
        return {
            "cells": [], "truncated": False, "n_cells_total": 0, "class_counts": {},
            "year_range": year_range, "recent_window": recent_range,
            "notes": ["No cells meet the minimum activity threshold."] + ([excl_note] if excl_note else []),
        }

    out = _classify_cells(matrix, years)

    class_counts = {str(k): int(v) for k, v in out["memory_class"].value_counts().items()}

    if memory_class:
        out = out[out["memory_class"] == memory_class]

    out = out.sort_values(["recurrence", "total_activity"], ascending=[False, False])
    total_cells = len(out)
    truncated = total_cells > limit

    cells = []
    for row in out.head(limit).itertuples():
        cells.append({
            "h3_cell": str(row.h3_cell),
            "recurrence": num(row.recurrence),
            "years_active": int(row.years_active),
            "years_in_range": int(row.years_in_range),
            "trend_slope": num(row.trend_slope),
            "memory_class": row.memory_class,
            "total_activity": num(row.total_activity),
            "first_active_year": int(row.first_active_year) if row.first_active_year else None,
            "last_active_year": int(row.last_active_year) if row.last_active_year else None,
        })

    notes = [
        f"Recent window = last {recent_window} complete years; "
        f"the early period is the {n_years - recent_window} year(s) before it."
    ]
    if n_years - recent_window < 2:
        notes.append("The early period is a single year, so declining/emerging labels are weakly supported.")
    if excl_note:
        notes.append(excl_note)
    if recent_window < 3:
        notes.append("The recent window contains fewer than three years; recent trend slopes are unavailable.")
    if memory_class:
        notes.append(f"Results are filtered to the '{memory_class}' memory class.")

    return {
        "cells": cells,
        "truncated": truncated,
        "n_cells_total": int(total_cells),
        "class_counts": class_counts,
        "year_range": year_range,
        "recent_window": recent_range,
        "notes": notes,
    }


def cell_timeline(repo, h3_id: str, region_id) -> dict:
    df = _prepare_data(repo.get_harmonized(region_id))
    if df.empty:
        raise TerraFlareError("no_data", "No valid harmonized data for this region", 404)

    h3_id = str(h3_id)
    complete, excluded = _complete_years(repo, df)

    cell_data = df[(df["h3_cell"] == h3_id) & (df["acq_date"].dt.year.isin(complete))].copy()
    if cell_data.empty:
        raise TerraFlareError("cell_not_found", f"No activity recorded for cell '{h3_id}'", 404)

    for column in ("harmonized_lower", "harmonized_upper"):
        if column not in cell_data.columns:
            cell_data[column] = np.nan
        else:
            cell_data[column] = pd.to_numeric(cell_data[column], errors="coerce")

    cell_data["year"] = cell_data["acq_date"].dt.year
    grouped = cell_data.groupby("year").agg(
        value=("harmonized_value", "sum"),
        lower=("harmonized_lower", lambda s: s.sum(min_count=1)),
        upper=("harmonized_upper", lambda s: s.sum(min_count=1)),
    )

    annual = []
    for year in complete:
        if year in grouped.index:
            row = grouped.loc[year]
            annual.append({"year": int(year), "harmonized_value": num(row["value"]),
                           "lower": num(row["lower"]), "upper": num(row["upper"])})
        else:
            annual.append({"year": int(year), "harmonized_value": 0.0, "lower": None, "upper": None})

    notes = [
        "Years with value 0 had full satellite coverage but no detections in this cell (not proof of no fire).",
        "Harmonized values are NOAA-20 observations, so no uncertainty bounds apply.",
    ]
    if excluded:
        notes.append(f"Incomplete years not shown (missing coverage): {excluded}.")
    return {"h3_cell": h3_id, "annual": annual, "notes": notes}