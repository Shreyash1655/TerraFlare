"""Temporal aggregation: aggregates canonical observations into cell-day activity marts."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from app.core.spatial.grid import assign_h3_cells
from app.shared.config_loader import get_harmonization_config


def aggregate_cell_day_activity(
    df: pd.DataFrame,
    date_col: str | None = None,
    valid_only: bool = True,
) -> pd.DataFrame:
    """Aggregate cleaned canonical observations to cell_day_activity.

    Grouped by:
      source_id, platform, h3_cell, date_col (local_date or acq_date), day_night

    Aggregated columns:
      n_detections: total count of detections
      n_high_conf: count of detections with confidence_class == 'high'
      frp_sum_mw: sum of frp_mw (MW)
      frp_max_mw: maximum frp_mw (MW)

    Never combines sensors or platforms.
    """
    if df.empty:
        cols = [
            "source_id", "sensor_family", "platform", "h3_cell",
            "date", "day_night", "n_detections", "n_high_conf",
            "frp_sum_mw", "frp_max_mw",
        ]
        return pd.DataFrame(columns=cols)

    # Filter valid rows only if requested
    data = df.copy()
    if valid_only and "is_valid" in data.columns:
        data = data[data["is_valid"].fillna(False).astype(bool)]

    # Exclude static masked observations (archive type 2/3 and NRT in static mask)
    if "static_masked" in data.columns:
        data = data[data["static_masked"].fillna(False) != True]
    if "qc_flags" in data.columns:
        data = data[~data["qc_flags"].astype(str).str.contains("possible_static_source", na=False)]

    if data.empty:
        cols = [
            "source_id", "sensor_family", "platform", "h3_cell",
            "date", "day_night", "n_detections", "n_high_conf",
            "frp_sum_mw", "frp_max_mw",
        ]
        return pd.DataFrame(columns=cols)

    # Ensure H3 cells are assigned
    if "h3_cell" not in data.columns or data["h3_cell"].isna().all():
        data = assign_h3_cells(data)

    # Filter out rows with null h3_cell
    data = data[data["h3_cell"].notna()]
    if data.empty:
        return pd.DataFrame()

    # Determine date column
    target_date_col = date_col
    if target_date_col is None:
        rule = get_harmonization_config().get("local_date_rule", "solar")
        target_date_col = "local_date" if rule == "solar" and "local_date" in data.columns else "acq_date"

    if target_date_col not in data.columns or data[target_date_col].isna().all():
        target_date_col = "acq_date"

    # Normalize date values to date or string
    dates = pd.to_datetime(data[target_date_col]).dt.date

    # Prepare fields for aggregation
    data["_target_date"] = pd.to_datetime(dates)
    data["_is_high_conf"] = (data["confidence_class"].astype(str).str.lower() == "high").astype(int)

    # Ensure frp_mw is numeric
    frp_numeric = pd.to_numeric(data["frp_mw"], errors="coerce")
    data["_frp"] = frp_numeric
    data["_is_nrt"] = (
        (data["processing_stream"].astype(str).str.upper() == "NRT").astype(int)
        if "processing_stream" in data.columns
        else 0
    )

    group_keys = ["source_id", "sensor_family", "platform", "h3_cell", "_target_date", "day_night"]
    # Handle missing day_night safely
    if "day_night" not in data.columns:
        data["day_night"] = "unknown"

    grouped = data.groupby(group_keys, dropna=False)

    agg_df = grouped.agg(
        n_detections=("obs_id", "count"),
        n_high_conf=("_is_high_conf", "sum"),
        frp_sum_mw=("_frp", "sum"),
        frp_max_mw=("_frp", "max"),
        is_provisional=("_is_nrt", "max"),
    ).reset_index()

    agg_df["frp_sum_mw"] = agg_df["frp_sum_mw"].round(4)
    agg_df["frp_max_mw"] = agg_df["frp_max_mw"].round(4)
    agg_df["is_provisional"] = agg_df["is_provisional"].astype(bool)

    # Rename _target_date back to standard date name
    agg_df = agg_df.rename(columns={"_target_date": "date"})
    agg_df[target_date_col] = agg_df["date"]

    return agg_df


def count_unique_active_cells_per_platform_day(
    cell_day_or_obs_df: pd.DataFrame,
    region_cells: Iterable[str] | None = None,
    date_col: str = "date",
) -> pd.DataFrame:
    """Calculate the number of unique active H3 cells per platform and day.

    Never combines sensors or platforms.
    """
    if cell_day_or_obs_df.empty:
        return pd.DataFrame(columns=["source_id", "platform", date_col, "n_active_cells"])

    df = cell_day_or_obs_df.copy()
    if date_col not in df.columns:
        if "local_date" in df.columns:
            df[date_col] = df["local_date"]
        elif "acq_date" in df.columns:
            df[date_col] = df["acq_date"]

    # Filter to region cells if specified
    if region_cells is not None:
        cells_set = set(region_cells)
        df = df[df["h3_cell"].isin(cells_set)]

    if df.empty:
        return pd.DataFrame(columns=["source_id", "platform", date_col, "n_active_cells"])

    group_keys = ["source_id", "platform", date_col]
    res = (
        df.groupby(group_keys, dropna=False)["h3_cell"]
        .nunique()
        .reset_index(name="n_active_cells")
    )
    return res

