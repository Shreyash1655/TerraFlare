"""Feature 6 - Sensor Confidence and Data Quality (the honesty layer)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.utils.response import num, to_records


LIMITATIONS = [
    "Detection confidence (is it fire?) and observation coverage (did the satellite look?) are different things.",
    "Native confidence scales differ between sensors and are never merged; the normalised class is shown separately.",
    "Coverage is taken from ingested file date ranges (see /harmonization/coverage), never inferred from missing detections.",
    "Missing detections never prove that no fire occurred, and never prove a coverage gap.",
    "MODIS and VIIRS counts are never added together; shares are computed within each sensor only.",
]


def _prepare_observations(obs: pd.DataFrame) -> pd.DataFrame:
    """Normalize observation dates and optional sensor fields."""
    if obs is None or obs.empty:
        return pd.DataFrame(
            columns=["acq_date", "sensor_family", "platform", "confidence_raw", "confidence_class"]
        )

    result = obs.copy()
    if "acq_date" not in result.columns:
        return pd.DataFrame()

    result["acq_date"] = pd.to_datetime(result["acq_date"], errors="coerce").dt.normalize()
    result = result.dropna(subset=["acq_date"])

    for col in ("sensor_family", "platform"):
        if col not in result.columns:
            result[col] = "unknown"
        else:
            result[col] = result[col].fillna("unknown").astype(str)

    for column in ("confidence_raw", "confidence_class"):
        if column not in result.columns:
            result[column] = np.nan

    return result.reset_index(drop=True)


def _contribution(obs: pd.DataFrame) -> list[dict]:
    """Monthly counts per sensor and platform.

    share = platform count / that sensor's total in the month. Never computed
    across sensors, so raw MODIS and VIIRS counts are not combined.
    """
    if obs.empty:
        return []

    data = obs.copy()
    data["period"] = data["acq_date"].dt.to_period("M").astype(str)

    grouped = (
        data.groupby(["period", "sensor_family", "platform"], dropna=False)
        .size()
        .rename("count")
        .reset_index()
    )
    totals = grouped.groupby(["period", "sensor_family"])["count"].transform("sum")
    grouped["share"] = (grouped["count"] / totals).round(4)

    return to_records(grouped)


def _confidence(obs: pd.DataFrame):
    """Summarize native and normalized confidence separately."""
    native = []
    normalized = []

    if obs.empty:
        return native, normalized

    if "confidence_raw" in obs.columns:
        d = obs.copy()
        d["native_class"] = d["confidence_raw"].where(d["confidence_raw"].notna(), "unknown").astype(str)
        native = to_records(
            d.groupby(["sensor_family", "native_class"], dropna=False)
            .size().rename("count").reset_index()
        )

    if "confidence_class" in obs.columns:
        d = obs.copy()
        d["confidence_class"] = d["confidence_class"].where(d["confidence_class"].notna(), "unknown").astype(str)
        normalized = to_records(
            d.groupby(["sensor_family", "confidence_class"], dropna=False)
            .size().rename("count").reset_index()
        )

    return native, normalized


def _availability(obs: pd.DataFrame) -> list[dict]:
    """Intentionally empty.

    Gaps used to be inferred from days without detections, which breaks the
    rule that coverage is never inferred from absence of hotspots. Coverage
    comes from ingested file ranges via /harmonization/coverage.
    """
    return []


def _uncertainty(repo, region_id, start, end) -> dict:
    """Summarize harmonization uncertainty and validation metadata."""
    harmonized = repo.get_harmonized(region_id, start, end)
    info = repo.get_calibration_info() or {}

    interval_level = None
    relative_width = None

    if harmonized is None or harmonized.empty:
        harmonized = pd.DataFrame()

    if "interval_level" in harmonized.columns and harmonized["interval_level"].notna().any():
        vals = pd.to_numeric(harmonized["interval_level"], errors="coerce").dropna()
        if not vals.empty:
            interval_level = num(vals.mode().iloc[0])

    required_bounds = {"harmonized_value", "harmonized_lower", "harmonized_upper"}
    if required_bounds.issubset(harmonized.columns):
        values = harmonized[list(required_bounds)].apply(pd.to_numeric, errors="coerce")
        positive = values[values["harmonized_value"] > 0]
        if not positive.empty:
            widths = (positive["harmonized_upper"] - positive["harmonized_lower"]) / positive["harmonized_value"]
            widths = widths.replace([np.inf, -np.inf], np.nan).dropna()
            if not widths.empty:
                relative_width = num(widths.median())

    validation = info.get("validation", []) or []
    note = None if validation else (
        "No held-out validation metrics available yet; none are shown rather than invented."
    )

    return {
        "method_id": info.get("method_id"),
        "interval_level": interval_level,
        "median_relative_width": relative_width,
        "validation": validation,
        "note": note,
    }


def compute_quality(repo, region_id, start, end, sensors) -> dict:
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    if start > end:
        from app.utils.errors import TerraFlareError
        raise TerraFlareError("invalid_date_range", "Start date must not be after end date.", 400)

    obs = _prepare_observations(repo.get_observations(region_id, start, end, sensors))
    native, normalized = _confidence(obs)

    notes = []
    if obs.empty:
        notes.append("No valid detections in this range.")
    notes.append(
        "Coverage gaps are not inferred here. Use /harmonization/coverage, which is based on ingested file ranges."
    )
    notes.append("Missing detections do not prove a coverage gap or the absence of fire.")

    return {
        "sensor_contribution": _contribution(obs),
        "confidence_distribution": native,
        "confidence_normalised": normalized,
        "availability": _availability(obs),
        "uncertainty_summary": _uncertainty(repo, region_id, start, end),
        "notes": notes,
    }


def provenance(repo) -> dict:
    """Return source-file and ingestion provenance records."""
    df = repo.get_provenance()
    if df is None or df.empty:
        return {"sources": []}

    columns = ["source_id", "product_version", "file_name", "sha256", "rows_in", "ingested_at"]
    rows = to_records(df[[c for c in columns if c in df.columns]])

    for row in rows:
        if row.get("rows_in") is not None:
            try:
                row["rows_in"] = int(row["rows_in"])
            except (TypeError, ValueError):
                row["rows_in"] = None
        if row.get("ingested_at") is not None:
            row["ingested_at"] = str(row["ingested_at"])

    return {"sources": rows}