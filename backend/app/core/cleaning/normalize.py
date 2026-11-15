"""Normalisation module for TerraFlare: confidence scores and local solar time."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.shared.config_loader import get_harmonization_config, get_sources

# Standard confidence classes
CONFIDENCE_CLASSES = ("low", "nominal", "high", "unknown")


def normalize_confidence_modis(
    val: Any,
    low_thresh: int = 30,
    high_thresh: int = 80,
) -> str:
    """Normalise MODIS numeric confidence (0-100) into low, nominal, high.

    Thresholds:
      - strictly below low_thresh (< 30) -> "low"
      - between low_thresh and high_thresh inclusive [30, 80] -> "nominal"
      - strictly above high_thresh (> 80) -> "high"

    Boundary cases:
      29 -> low
      30 -> nominal
      80 -> nominal
      81 -> high
    """
    if val is None or pd.isna(val) or val == "":
        return "unknown"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return "unknown"

    if num < low_thresh:
        return "low"
    elif num <= high_thresh:
        return "nominal"
    else:
        return "high"


def normalize_confidence_viirs(val: Any) -> str:
    """Normalise VIIRS categorical confidence into low, nominal, high.

    Maps:
      - 'l' or 'low' -> 'low'
      - 'n' or 'nominal' -> 'nominal'
      - 'h' or 'high' -> 'high'
      - any other value -> 'unknown'
    """
    if val is None or pd.isna(val) or val == "":
        return "unknown"
    s = str(val).strip().lower()
    if s in ("l", "low"):
        return "low"
    elif s in ("n", "nominal"):
        return "nominal"
    elif s in ("h", "high"):
        return "high"
    return "unknown"


def compute_solar_local_date(
    acq_datetime_utc: datetime | pd.Timestamp,
    lon: float,
) -> date:
    """Compute local date from longitude (UTC time plus lon/15 hours).

    15 degrees of longitude corresponds to 1 hour of local solar time.
    acq_date remains in UTC; local_date can differ near midnight.
    """
    if pd.isna(acq_datetime_utc) or acq_datetime_utc is None:
        raise ValueError("acq_datetime_utc cannot be null for solar date calculation")
    if pd.isna(lon) or lon is None:
        raise ValueError("longitude cannot be null for solar date calculation")

    hours_offset = float(lon) / 15.0
    local_time = acq_datetime_utc + timedelta(hours=hours_offset)
    return local_time.date()


def normalize_canonical_dataframe(
    df: pd.DataFrame,
    sources_cfg: dict[str, Any] | None = None,
    local_date_rule: str | None = None,
) -> pd.DataFrame:
    """Normalise confidence_class and local_date for a canonical DataFrame.

    - Modifies confidence_class while keeping confidence_raw untouched.
    - Modifies local_date while keeping acq_date untouched.
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    sources = sources_cfg if sources_cfg is not None else get_sources()

    # Determine thresholds from config if available
    modis_low = 30
    modis_high = 80
    modis_cfg = sources.get("modis_c61", {})
    conf_map = modis_cfg.get("confidence_map", {})
    if "low_threshold" in conf_map:
        modis_low = int(conf_map["low_threshold"])
    if "high_threshold" in conf_map:
        modis_high = int(conf_map["high_threshold"])

    # 1. Normalise confidence_class per sensor separately
    is_modis = out["sensor_family"].str.upper() == "MODIS"
    is_viirs = out["sensor_family"].str.upper() == "VIIRS"

    classes = pd.Series("unknown", index=out.index, dtype=object)

    if is_modis.any():
        classes.loc[is_modis] = out.loc[is_modis, "confidence_raw"].apply(
            lambda v: normalize_confidence_modis(v, low_thresh=modis_low, high_thresh=modis_high)
        )

    if is_viirs.any():
        classes.loc[is_viirs] = out.loc[is_viirs, "confidence_raw"].apply(
            normalize_confidence_viirs
        )

    # Any other sensor family fallback
    other = ~(is_modis | is_viirs)
    if other.any():
        classes.loc[other] = out.loc[other, "confidence_raw"].apply(
            lambda v: normalize_confidence_viirs(v) if str(v).lower() in ("l", "n", "h", "low", "nominal", "high") else normalize_confidence_modis(v)
        )

    out["confidence_class"] = classes

    # 2. Compute local_date if rule is 'solar'
    rule = local_date_rule
    if rule is None:
        rule = get_harmonization_config().get("local_date_rule", "solar")

    if rule == "solar" and "acq_datetime_utc" in out.columns and "lon" in out.columns:
        dt_col = pd.to_datetime(out["acq_datetime_utc"])
        lon_col = pd.to_numeric(out["lon"], errors="coerce")

        # Vectorised computation of local solar datetime
        valid_mask = dt_col.notna() & lon_col.notna()
        local_dates = pd.Series(None, index=out.index, dtype=object)

        if valid_mask.any():
            offsets = pd.to_timedelta(lon_col[valid_mask] / 15.0, unit="h")
            local_dt = dt_col[valid_mask] + offsets
            local_dates.loc[valid_mask] = local_dt.dt.date

        out["local_date"] = pd.to_datetime(local_dates)

    return out

