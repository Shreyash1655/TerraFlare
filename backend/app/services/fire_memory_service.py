
"""Feature 2 - Fire Memory Map (recurrence classes per grid cell)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import settings
from app.utils.errors import TerraFlareError
from app.utils.response import num
from app.utils.stats import theil_sen_slope


LIMITATIONS = [
    "Recurrence means detections occurred in a cell in several years, not that the same fire recurred.",
    "Persistent industrial, volcanic or gas-flare heat sources may appear as 'persistent' (no land-cover mask).",
    "Cell size and thresholds are descriptive choices, not scientific constants.",
]


MEMORY_CLASSES = {
    "persistent",
    "emerging",
    "declining",
    "sporadic",
}


def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the harmonized dataset."""

    required = {
        "h3_cell",
        "acq_date",
        "harmonized_value",
    }

    missing = required - set(df.columns)

    if missing:
        raise TerraFlareError(
            "invalid_data",
            f"Missing required columns: {sorted(missing)}",
            500,
        )

    result = df.copy()

    result["acq_date"] = pd.to_datetime(
        result["acq_date"],
        errors="coerce",
    )

    result["harmonized_value"] = pd.to_numeric(
        result["harmonized_value"],
        errors="coerce",
    )

    result = result.dropna(
        subset=["h3_cell", "acq_date", "harmonized_value"]
    )

    result["h3_cell"] = result["h3_cell"].astype(str)
    result["acq_date"] = result["acq_date"].dt.normalize()

    result = result[
        np.isfinite(result["harmonized_value"])
    ]

    return result


def _annual_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build a cell-by-year activity matrix."""

    d = df[
        ["h3_cell", "harmonized_value", "acq_date"]
    ].copy()

    d["year"] = d["acq_date"].dt.year

    matrix = (
        d.groupby(["h3_cell", "year"])["harmonized_value"]
        .sum()
        .unstack(fill_value=0.0)
    )

    if matrix.empty:
        return matrix

    first_year = int(d["year"].min())
    last_year = int(d["year"].max())

    years = list(range(first_year, last_year + 1))

    matrix = matrix.reindex(
        columns=years,
        fill_value=0.0,
    )

    return matrix


def _classify_cells(
    matrix: pd.DataFrame,
    years: np.ndarray,
) -> pd.DataFrame:
    """Calculate recurrence metrics and assign memory classes."""

    values = matrix.to_numpy(dtype=float)

    active = values > 0

    n_years = len(years)

    recent_window = min(
        settings.memory_recent_window_years,
        n_years - 1,
    )

    split = n_years - recent_window

    early_values = values[:, :split]
    recent_values = values[:, split:]

    early_active = active[:, :split]
    recent_active = active[:, split:]

    early_recurrence = early_active.mean(axis=1)

    early_mean = early_values.mean(axis=1)
    recent_mean = recent_values.mean(axis=1)

    recent_active_years = recent_active.sum(axis=1)

    recurrence = active.sum(axis=1) / n_years

    overall_mean = values.mean(axis=1)

    # Calculate recent activity trend.
    if recent_window >= 3:
        slopes = np.array(
            [
                theil_sen_slope(
                    years[split:],
                    row,
                )
                for row in recent_values
            ],
            dtype=float,
        )
    else:
        slopes = np.full(
            len(matrix),
            np.nan,
            dtype=float,
        )

    # Normalize trend by average annual activity.
    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        relative_trend = slopes / overall_mean

    relative_trend = np.nan_to_num(
        relative_trend,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    strong = settings.memory_strong_trend

    declining = (
        (early_mean > 0)
        & (
            (relative_trend <= -strong)
            | (
                recent_mean
                <= settings.memory_drop_ratio * early_mean
            )
        )
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
        [
            persistent,
            emerging,
            declining,
        ],
        [
            "persistent",
            "emerging",
            "declining",
        ],
        default="sporadic",
    )

    # Identify first and last active years.
    has_activity = active.any(axis=1)

    first_active = np.zeros(
        len(matrix),
        dtype=int,
    )

    last_active = np.zeros(
        len(matrix),
        dtype=int,
    )

    if has_activity.any():
        first_indices = np.argmax(
            active[has_activity],
            axis=1,
        )

        last_indices = (
            n_years
            - 1
            - np.argmax(
                active[has_activity, ::-1],
                axis=1,
            )
        )

        first_active[has_activity] = years[first_indices]
        last_active[has_activity] = years[last_indices]

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


def compute_cells(
    repo,
    region_id,
    memory_class,
    min_activity,
    limit,
) -> dict:

    df = _prepare_data(
        repo.get_harmonized(region_id)
    )

    if df.empty:
        raise TerraFlareError(
            "no_data",
            "No valid harmonized data for this region",
            404,
        )

    if memory_class is not None and memory_class not in MEMORY_CLASSES:
        raise TerraFlareError(
            "invalid_memory_class",
            f"Unknown memory class: {memory_class}",
            400,
        )

    if limit < 1:
        raise TerraFlareError(
            "invalid_limit",
            "Limit must be at least 1",
            400,
        )

    if min_activity < 0:
        raise TerraFlareError(
            "invalid_min_activity",
            "Minimum activity cannot be negative",
            400,
        )

    matrix = _annual_matrix(df)

    years = np.array(
        matrix.columns,
        dtype=int,
    )

    n_years = len(years)

    if n_years < settings.memory_min_years:
        raise TerraFlareError(
            "insufficient_years",
            f"Fire memory needs at least {settings.memory_min_years} years",
            422,
        )

    recent_window = min(
        settings.memory_recent_window_years,
        n_years - 1,
    )

    # Remove cells below the requested activity threshold.
    matrix = matrix[
        matrix.sum(axis=1) >= min_activity
    ]

    if matrix.empty:
        return {
            "cells": [],
            "truncated": False,
            "n_cells_total": 0,
            "class_counts": {},
            "year_range": [
                int(years[0]),
                int(years[-1]),
            ],
            "recent_window": [
                int(years[-recent_window]),
                int(years[-1]),
            ],
            "notes": [
                "No cells meet the minimum activity threshold."
            ],
        }

    out = _classify_cells(
        matrix,
        years,
    )

    # Calculate counts before applying the optional class filter.
    class_counts = {
        str(key): int(value)
        for key, value in out["memory_class"].value_counts().items()
    }

    if memory_class:
        out = out[
            out["memory_class"] == memory_class
        ]

    out = out.sort_values(
        ["recurrence", "total_activity"],
        ascending=[False, False],
    )

    total_cells = len(out)

    truncated = total_cells > limit

    cells = []

    for row in out.head(limit).itertuples():

        cells.append(
            {
                "h3_cell": str(row.h3_cell),
                "recurrence": num(row.recurrence),
                "years_active": int(row.years_active),
                "years_in_range": int(row.years_in_range),
                "trend_slope": num(row.trend_slope),
                "memory_class": row.memory_class,
                "total_activity": num(row.total_activity),
                "first_active_year": (
                    int(row.first_active_year)
                    if row.first_active_year
                    else None
                ),
                "last_active_year": (
                    int(row.last_active_year)
                    if row.last_active_year
                    else None
                ),
            }
        )

    notes = [
        f"Recent window = last {recent_window} years; earlier years form the early period."
    ]

    first_date = df["acq_date"].min()
    last_date = df["acq_date"].max()

    first_year_start = pd.Timestamp(
        int(years[0]), 1, 1
    )

    last_year_end = pd.Timestamp(
        int(years[-1]), 12, 31
    )

    if (
        first_date > first_year_start
        or last_date < last_year_end
    ):
        notes.append(
            "The first or last year is only partly covered, "
            "which can lower recurrence."
        )

    if recent_window < 3:
        notes.append(
            "The recent window contains fewer than three years; "
            "recent trend slopes are unavailable."
        )

    if memory_class:
        notes.append(
            f"Results are filtered to the '{memory_class}' memory class."
        )

    return {
        "cells": cells,
        "truncated": truncated,
        "n_cells_total": int(total_cells),
        "class_counts": class_counts,
        "year_range": [
            int(years[0]),
            int(years[-1]),
        ],
        "recent_window": [
            int(years[-recent_window]),
            int(years[-1]),
        ],
        "notes": notes,
    }


def cell_timeline(
    repo,
    h3_id: str,
    region_id,
) -> dict:

    df = _prepare_data(
        repo.get_harmonized(region_id)
    )

    if df.empty:
        raise TerraFlareError(
            "no_data",
            "No valid harmonized data for this region",
            404,
        )

    h3_id = str(h3_id)

    cell_data = df[
        df["h3_cell"] == h3_id
    ].copy()

    if cell_data.empty:
        raise TerraFlareError(
            "cell_not_found",
            f"No activity recorded for cell '{h3_id}'",
            404,
        )

    # Handle optional uncertainty columns.
    for column in (
        "harmonized_lower",
        "harmonized_upper",
    ):
        if column not in cell_data.columns:
            cell_data[column] = np.nan
        else:
            cell_data[column] = pd.to_numeric(
                cell_data[column],
                errors="coerce",
            )

    first_year = int(
        df["acq_date"].dt.year.min()
    )

    last_year = int(
        df["acq_date"].dt.year.max()
    )

    cell_data["year"] = (
        cell_data["acq_date"].dt.year
    )

    grouped = (
        cell_data.groupby("year")
        .agg(
            value=("harmonized_value", "sum"),
            lower=(
                "harmonized_lower",
                lambda series: series.sum(min_count=1),
            ),
            upper=(
                "harmonized_upper",
                lambda series: series.sum(min_count=1),
            ),
        )
    )

    annual = []

    for year in range(
        first_year,
        last_year + 1,
    ):

        if year in grouped.index:
            row = grouped.loc[year]

            annual.append(
                {
                    "year": int(year),
                    "harmonized_value": num(row["value"]),
                    "lower": num(row["lower"]),
                    "upper": num(row["upper"]),
                }
            )

        else:
            annual.append(
                {
                    "year": int(year),
                    "harmonized_value": 0.0,
                    "lower": None,
                    "upper": None,
                }
            )

    return {
        "h3_cell": h3_id,
        "annual": annual,
        "notes": [
            "Years with value 0 have no detections recorded for this cell (not proof of no fire).",
            "Uncertainty bounds are unavailable for years without recorded observations.",
        ],
    }
