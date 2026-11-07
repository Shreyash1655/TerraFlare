
"""Feature 6 - Sensor Confidence and Data Quality (the honesty layer)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import settings
from app.utils.response import iso, num, to_records


LIMITATIONS = [
    "Detection confidence (is it fire?) and observation coverage (did the satellite look?) are different things.",
    "Native confidence scales differ between sensors and are never merged; the normalised class is shown separately.",
    "Gaps are 'no detections recorded' periods and only POSSIBLE coverage gaps, not proof.",
    "Missing detections never prove that no fire occurred.",
]

GAP_LABEL = "no detections recorded (possible coverage gap)"


def _prepare_observations(obs: pd.DataFrame) -> pd.DataFrame:
    """Normalize observation dates and optional sensor fields."""

    if obs is None or obs.empty:
        return pd.DataFrame(
            columns=[
                "acq_date",
                "sensor_family",
                "platform",
                "confidence_raw",
                "confidence_class",
            ]
        )

    result = obs.copy()

    if "acq_date" not in result.columns:
        return pd.DataFrame()

    result["acq_date"] = pd.to_datetime(
        result["acq_date"],
        errors="coerce",
    ).dt.normalize()

    result = result.dropna(
        subset=["acq_date"]
    )

    if "sensor_family" not in result.columns:
        result["sensor_family"] = "unknown"
    else:
        result["sensor_family"] = (
            result["sensor_family"]
            .fillna("unknown")
            .astype(str)
        )

    if "platform" not in result.columns:
        result["platform"] = "unknown"
    else:
        result["platform"] = (
            result["platform"]
            .fillna("unknown")
            .astype(str)
        )

    for column in (
        "confidence_raw",
        "confidence_class",
    ):
        if column not in result.columns:
            result[column] = np.nan

    return result.reset_index(drop=True)


def _contribution(obs: pd.DataFrame) -> list[dict]:
    """Calculate monthly sensor and platform contribution shares."""

    if obs.empty:
        return []

    data = obs.copy()

    data["period"] = (
        data["acq_date"]
        .dt.to_period("M")
        .astype(str)
    )

    grouped = (
        data.groupby(
            ["period", "sensor_family", "platform"],
            dropna=False,
        )
        .size()
        .rename("count")
        .reset_index()
    )

    totals = grouped.groupby("period")["count"].transform(
        "sum"
    )

    grouped["share"] = (
        grouped["count"] / totals
    ).round(4)

    return to_records(grouped)


def _confidence(
    obs: pd.DataFrame,
):
    """Summarize native and normalized confidence separately."""

    native = []
    normalized = []

    if obs.empty:
        return native, normalized

    if "confidence_raw" in obs.columns:

        native_data = obs.copy()

        native_data["native_class"] = (
            native_data["confidence_raw"]
            .where(
                native_data["confidence_raw"].notna(),
                "unknown",
            )
            .astype(str)
        )

        native_grouped = (
            native_data.groupby(
                ["sensor_family", "native_class"],
                dropna=False,
            )
            .size()
            .rename("count")
            .reset_index()
        )

        native = to_records(
            native_grouped
        )

    if "confidence_class" in obs.columns:

        normalized_data = obs.copy()

        normalized_data["confidence_class"] = (
            normalized_data["confidence_class"]
            .where(
                normalized_data["confidence_class"].notna(),
                "unknown",
            )
            .astype(str)
        )

        normalized_grouped = (
            normalized_data.groupby(
                ["sensor_family", "confidence_class"],
                dropna=False,
            )
            .size()
            .rename("count")
            .reset_index()
        )

        normalized = to_records(
            normalized_grouped
        )

    return native, normalized


def _availability(
    obs: pd.DataFrame,
) -> list[dict]:
    """Identify unusually long gaps between recorded detections."""

    gaps_out = []

    if obs.empty:
        return gaps_out

    for sensor, group in obs.groupby(
        "sensor_family"
    ):

        days = np.sort(
            group["acq_date"]
            .dt.normalize()
            .dropna()
            .unique()
        )

        if len(days) < 2:
            continue

        gaps = (
            np.diff(days)
            .astype("timedelta64[D]")
            .astype(int)
            - 1
        )

        if len(gaps) == 0:
            continue

        usual_gap = float(
            np.median(gaps)
        )

        threshold = max(
            settings.quality_min_gap_days,
            float(
                np.quantile(
                    gaps,
                    settings.quality_gap_quantile,
                )
            ),
        )

        for index in np.nonzero(
            gaps >= threshold
        )[0]:

            gap_days = int(
                gaps[index]
            )

            if gap_days < settings.quality_min_gap_days:
                continue

            gap_start = (
                pd.Timestamp(days[index])
                + pd.Timedelta(days=1)
            )

            gap_end = (
                pd.Timestamp(days[index + 1])
                - pd.Timedelta(days=1)
            )

            gaps_out.append(
                {
                    "sensor_family": str(sensor),
                    "gap_start": iso(gap_start),
                    "gap_end": iso(gap_end),
                    "gap_days": gap_days,
                    "usual_gap_days": num(
                        usual_gap,
                        1,
                    ),
                    "label": GAP_LABEL,
                }
            )

    gaps_out.sort(
        key=lambda row: (
            row["gap_days"],
            row["gap_start"],
        ),
        reverse=True,
    )

    return gaps_out[
        :settings.quality_max_gaps
    ]


def _uncertainty(
    repo,
    region_id,
    start,
    end,
) -> dict:
    """Summarize harmonization uncertainty and validation metadata."""

    harmonized = repo.get_harmonized(
        region_id,
        start,
        end,
    )

    info = repo.get_calibration_info() or {}

    interval_level = None
    relative_width = None

    if harmonized is None or harmonized.empty:
        harmonized = pd.DataFrame()

    if (
        "interval_level" in harmonized.columns
        and harmonized["interval_level"].notna().any()
    ):

        interval_values = pd.to_numeric(
            harmonized["interval_level"],
            errors="coerce",
        ).dropna()

        if not interval_values.empty:
            interval_level = num(
                interval_values.mode().iloc[0]
            )

    required_bounds = {
        "harmonized_value",
        "harmonized_lower",
        "harmonized_upper",
    }

    if required_bounds.issubset(
        harmonized.columns
    ):

        values = harmonized[
            [
                "harmonized_value",
                "harmonized_lower",
                "harmonized_upper",
            ]
        ].apply(
            pd.to_numeric,
            errors="coerce",
        )

        positive = values[
            values["harmonized_value"] > 0
        ]

        if not positive.empty:

            widths = (
                positive["harmonized_upper"]
                - positive["harmonized_lower"]
            ) / positive["harmonized_value"]

            widths = widths.replace(
                [np.inf, -np.inf],
                np.nan,
            ).dropna()

            if not widths.empty:
                relative_width = num(
                    widths.median()
                )

    validation = info.get(
        "validation",
        [],
    )

    if validation is None:
        validation = []

    note = (
        None
        if validation
        else (
            "No held-out validation metrics available yet; "
            "none are shown rather than invented."
        )
    )

    return {
        "method_id": info.get("method_id"),
        "interval_level": interval_level,
        "median_relative_width": relative_width,
        "validation": validation,
        "note": note,
    }


def compute_quality(
    repo,
    region_id,
    start,
    end,
    sensors,
) -> dict:

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    if start > end:
        from app.utils.errors import TerraFlareError

        raise TerraFlareError(
            "invalid_date_range",
            "Start date must not be after end date.",
            400,
        )

    observations = repo.get_observations(
        region_id,
        start,
        end,
        sensors,
    )

    obs = _prepare_observations(
        observations
    )

    native, normalized = _confidence(
        obs
    )

    notes = []

    if obs.empty:
        notes.append(
            "No valid detections in this range."
        )

    notes.append(
        "Gaps are detected only between a sensor's first and last detection inside the selected range."
    )

    notes.append(
        "A gap indicates no detections recorded, not confirmed satellite downtime."
    )

    return {
        "sensor_contribution": _contribution(obs),
        "confidence_distribution": native,
        "confidence_normalised": normalized,
        "availability": _availability(obs),
        "uncertainty_summary": _uncertainty(
            repo,
            region_id,
            start,
            end,
        ),
        "notes": notes,
    }


def provenance(repo) -> dict:
    """Return source-file and ingestion provenance records."""

    df = repo.get_provenance()

    if df is None or df.empty:
        return {
            "sources": [],
        }

    columns = [
        "source_id",
        "product_version",
        "file_name",
        "sha256",
        "rows_in",
        "ingested_at",
    ]

    available_columns = [
        column
        for column in columns
        if column in df.columns
    ]

    rows = to_records(
        df[available_columns]
    )

    for row in rows:

        if row.get("rows_in") is not None:
            try:
                row["rows_in"] = int(
                    row["rows_in"]
                )
            except (TypeError, ValueError):
                row["rows_in"] = None

        if row.get("ingested_at") is not None:
            row["ingested_at"] = str(
                row["ingested_at"]
            )

    return {
        "sources": rows,
    }
