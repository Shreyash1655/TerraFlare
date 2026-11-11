"""Validation and cleaning rules for TerraFlare canonical observations."""

from __future__ import annotations

import json
from typing import Any, Iterable

import numpy as np
import pandas as pd

from app.shared.config_loader import get_harmonization_config

# Confidence hierarchy for min_confidence filtering
CONFIDENCE_LEVELS: dict[str, int] = {
    "unknown": 0,
    "low": 1,
    "nominal": 2,
    "high": 3,
}

# Standard vegetation fire types (0 in FIRMS = presumed vegetation fire)
DEFAULT_ALLOWED_FIRE_TYPES: set[str] = {
    "0",
    "vegetation",
    "presumed vegetation fire",
}


def _append_qc_flag(existing: Any, new_flag: str) -> str:
    """Safely append a new flag to a JSON array string."""
    if not existing or pd.isna(existing) or existing == "":
        flags: list[str] = []
    elif isinstance(existing, list):
        flags = list(existing)
    else:
        try:
            parsed = json.loads(str(existing))
            flags = parsed if isinstance(parsed, list) else [str(parsed)]
        except (json.JSONDecodeError, ValueError):
            flags = [str(existing)]

    if new_flag not in flags:
        flags.append(new_flag)
    return json.dumps(flags)


def _apply_flag(df: pd.DataFrame, mask: pd.Series, flag_name: str) -> int:
    """Apply flag_name and set is_valid=False on masked rows in place. Returns count."""
    count = int(mask.sum())
    if count == 0:
        return 0

    df.loc[mask, "is_valid"] = False
    df.loc[mask, "qc_flags"] = df.loc[mask, "qc_flags"].apply(
        lambda existing: _append_qc_flag(existing, flag_name)
    )
    return count


# ---------------------------------------------------------------------------
# Individual cleaning rules
# ---------------------------------------------------------------------------

def check_coordinate_range(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Flag rows where latitude is not in [-90, 90] or longitude not in [-180, 180]."""
    out = df.copy()
    lat = pd.to_numeric(out["lat"], errors="coerce")
    lon = pd.to_numeric(out["lon"], errors="coerce")

    mask = lat.isna() | (lat < -90.0) | (lat > 90.0) | lon.isna() | (lon < -180.0) | (lon > 180.0)
    count = _apply_flag(out, mask, "invalid_coordinates")
    return out, count


def check_missing_date(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Flag rows where acq_date is missing or NaT."""
    out = df.copy()
    acq_date = pd.to_datetime(out["acq_date"], errors="coerce")
    mask = acq_date.isna()
    count = _apply_flag(out, mask, "missing_date")
    return out, count


def check_duplicate_obs_id(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Flag subsequent duplicate occurrences of obs_id."""
    out = df.copy()
    mask = out.duplicated(subset=["obs_id"], keep="first")
    count = _apply_flag(out, mask, "duplicate_obs_id")
    return out, count


def filter_fire_type(
    df: pd.DataFrame,
    allowed_types: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Flag non-vegetation fires (static sources, volcano, offshore) when fire_type exists.

    When fire_type is null or absent (e.g. NRT data), the row is NOT flagged.
    """
    out = df.copy()
    allowed = set(allowed_types) if allowed_types is not None else DEFAULT_ALLOWED_FIRE_TYPES
    allowed_str = {str(x).strip().lower() for x in allowed}

    if "fire_type" not in out.columns:
        return out, 0

    has_fire_type = out["fire_type"].notna() & (out["fire_type"] != "") & (out["fire_type"] != "None")
    types_clean = out["fire_type"].astype(str).str.strip().str.lower()
    mask = has_fire_type & (~types_clean.isin(allowed_str))

    count = _apply_flag(out, mask, "non_vegetation_fire")
    return out, count


def filter_confidence(
    df: pd.DataFrame,
    min_confidence_class: str | None = None,
) -> tuple[pd.DataFrame, int]:
    """Flag rows whose confidence_class is below min_confidence_class.

    Hierarchy: unknown (0) < low (1) < nominal (2) < high (3).
    """
    out = df.copy()
    min_class = min_confidence_class
    if min_class is None:
        min_class = get_harmonization_config().get("min_confidence_class", "nominal")

    min_level = CONFIDENCE_LEVELS.get(min_class.lower(), 2)

    if "confidence_class" not in out.columns:
        return out, 0

    classes = out["confidence_class"].fillna("unknown").astype(str).str.lower()
    levels = classes.map(CONFIDENCE_LEVELS).fillna(0)
    mask = levels < min_level

    count = _apply_flag(out, mask, "below_min_confidence")
    return out, count


def check_negative_frp(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Flag rows where Fire Radiative Power (frp_mw) is negative."""
    out = df.copy()
    if "frp_mw" not in out.columns:
        return out, 0

    frp = pd.to_numeric(out["frp_mw"], errors="coerce")
    mask = frp.notna() & (frp < 0.0)
    count = _apply_flag(out, mask, "negative_frp")
    return out, count


def check_duplicate_across_streams(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Flag NRT rows as duplicate_across_streams when an SP row exists for the same detection.

    A detection is identified by (source_id, platform, lat, lon, acq_date, acq_time) or obs_id.
    Keeps the SP row valid, marks the NRT row is_valid=False with flag 'duplicate_across_streams'.
    """
    if df.empty or "processing_stream" not in df.columns:
        return df, 0

    out = df.copy()
    stream = out["processing_stream"].astype(str).str.upper()
    is_sp = stream == "SP"
    is_nrt = stream == "NRT"

    if not is_sp.any() or not is_nrt.any():
        return out, 0

    # Key columns identifying the detection
    if "obs_id" in out.columns:
        sp_keys = set(out.loc[is_sp, "obs_id"])
        mask = is_nrt & out["obs_id"].isin(sp_keys)
    else:
        key_cols = ["source_id", "platform", "lat", "lon", "acq_date"]
        for t_col in ["acq_time_utc", "acq_datetime_utc", "acq_time"]:
            if t_col in out.columns:
                key_cols.append(t_col)
                break
        sp_keys = set(out.loc[is_sp, key_cols].itertuples(index=False, name=None))
        nrt_keys = list(out.loc[is_nrt, key_cols].itertuples(index=False, name=None))
        mask = pd.Series(False, index=out.index)
        nrt_indices = out.loc[is_nrt].index
        mask.loc[nrt_indices] = [k in sp_keys for k in nrt_keys]

    count = _apply_flag(out, mask, "duplicate_across_streams")
    return out, count


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def apply_cleaning_rules(
    df: pd.DataFrame,
    min_confidence_class: str | None = None,
    allowed_fire_types: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Execute all cleaning rules sequentially.

    Invalid rows are flagged (is_valid=False, flag added to qc_flags),
    NEVER silently deleted.

    Returns:
        (cleaned_df, report_records)
    """
    current_df = df.copy()
    reports: list[dict[str, Any]] = []

    # 1. Coordinate range
    current_df, count = check_coordinate_range(current_df)
    reports.append({"rule_id": "coordinate_range", "rows_flagged": count, "rows_dropped": 0})

    # 2. Missing date
    current_df, count = check_missing_date(current_df)
    reports.append({"rule_id": "missing_date", "rows_flagged": count, "rows_dropped": 0})

    # 3. Duplicate obs_id
    current_df, count = check_duplicate_obs_id(current_df)
    reports.append({"rule_id": "duplicate_obs_id", "rows_flagged": count, "rows_dropped": 0})

    # 4. Duplicate across streams (cross-stream deduplication: keep SP, flag NRT)
    current_df, count = check_duplicate_across_streams(current_df)
    reports.append({"rule_id": "duplicate_across_streams", "rows_flagged": count, "rows_dropped": 0})

    # 5. Fire type
    current_df, count = filter_fire_type(current_df, allowed_types=allowed_fire_types)
    reports.append({"rule_id": "fire_type_filter", "rows_flagged": count, "rows_dropped": 0})

    # 6. Confidence filter
    current_df, count = filter_confidence(current_df, min_confidence_class=min_confidence_class)
    reports.append({"rule_id": "confidence_filter", "rows_flagged": count, "rows_dropped": 0})

    # 7. Negative FRP
    current_df, count = check_negative_frp(current_df)
    reports.append({"rule_id": "negative_frp", "rows_flagged": count, "rows_dropped": 0})

    return current_df, reports

