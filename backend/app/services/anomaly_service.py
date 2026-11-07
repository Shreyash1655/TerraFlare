
"""Feature 3 - Explainable Anomaly Engine (statistical statement, never a cause)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import settings
from app.utils.errors import TerraFlareError
from app.utils.response import iso, num
from app.utils.stats import percentile_rank, robust_z


LIMITATIONS = [
    "An anomaly is a statistical statement about the record, not a cause.",
    "Baseline = same calendar window (+/- window_days) in all PRIOR years; periods without enough prior years are not scored.",
    "Scores use log1p(activity). Lower/upper z-scores show harmonization uncertainty of the observed value only.",
    "Contribution shares are relative to the sum of positive contributions.",
]


def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize harmonized data."""

    required = {
        "acq_date",
        "harmonized_value",
        "h3_cell",
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
    ).dt.normalize()

    result["harmonized_value"] = pd.to_numeric(
        result["harmonized_value"],
        errors="coerce",
    )

    result = result.dropna(
        subset=["acq_date", "harmonized_value"]
    )

    result = result[
        np.isfinite(result["harmonized_value"])
    ]

    result["h3_cell"] = result["h3_cell"].astype(str)

    for column in ("harmonized_lower", "harmonized_upper"):
        if column not in result.columns:
            result[column] = np.nan
        else:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    return result


def _daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate harmonized activity into a continuous daily series."""

    if df.empty:
        return pd.DataFrame(
            columns=["value", "lower", "upper"],
            index=pd.DatetimeIndex([]),
        )

    grouped = df.groupby("acq_date")

    value = grouped["harmonized_value"].sum()

    index = pd.date_range(
        value.index.min(),
        value.index.max(),
        freq="D",
    )

    out = pd.DataFrame(
        {
            "value": value.reindex(
                index,
                fill_value=0.0,
            )
        }
    )

    lower = grouped["harmonized_lower"].sum(
        min_count=1
    ).reindex(index)

    upper = grouped["harmonized_upper"].sum(
        min_count=1
    ).reindex(index)

    # Use the observed value when uncertainty bounds are unavailable.
    out["lower"] = lower.fillna(out["value"])
    out["upper"] = upper.fillna(out["value"])

    return out


def _windows(
    p_start,
    p_end,
    window_days,
    d0,
    d1,
):
    """Yield valid matching calendar windows from prior years only."""

    p_start = pd.Timestamp(p_start)
    p_end = pd.Timestamp(p_end)

    for dy in range(
        1,
        p_start.year - d0.year + 1,
    ):
        ws = (
            p_start
            - pd.DateOffset(years=dy)
            - pd.Timedelta(days=window_days)
        )

        we = (
            p_end
            - pd.DateOffset(years=dy)
            + pd.Timedelta(days=window_days)
        )

        if ws >= d0 and we <= d1:
            yield p_start.year - dy, ws, we


def _baseline(
    series: pd.Series,
    p_start,
    p_end,
    window_days,
    d0,
    d1,
) -> dict[int, float]:
    """Calculate historical activity scaled to the requested period length."""

    plen = (p_end - p_start).days + 1

    if plen <= 0:
        return {}

    result = {}

    for year, ws, we in _windows(
        p_start,
        p_end,
        window_days,
        d0,
        d1,
    ):
        window = series.loc[ws:we]

        if window.empty:
            continue

        result[year] = float(
            window.sum() * plen / len(window)
        )

    return result


def _score(
    observed,
    base_vals,
    min_years,
):
    """Return robust Z-score and historical percentile."""

    if len(base_vals) < min_years:
        return None, None

    baseline = np.asarray(
        base_vals,
        dtype=float,
    )

    baseline = baseline[
        np.isfinite(baseline)
        & (baseline >= 0)
    ]

    if len(baseline) < min_years:
        return None, None

    if not np.isfinite(observed) or observed < 0:
        return None, None

    z = robust_z(
        np.log1p(observed),
        np.log1p(baseline),
    )

    percentile = percentile_rank(
        observed,
        baseline,
    )

    return z, percentile


def _validate_period(
    start,
    end,
    window_days,
):
    """Validate date ranges and historical window size."""

    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()

    if start > end:
        raise TerraFlareError(
            "invalid_date_range",
            "Start date must not be after end date",
            400,
        )

    if window_days < 0:
        raise TerraFlareError(
            "invalid_window",
            "Window days cannot be negative",
            400,
        )

    return start, end


def list_anomalies(
    repo,
    region_id,
    start,
    end,
    period_days,
    window_days,
) -> dict:

    if period_days < 1:
        raise TerraFlareError(
            "invalid_period",
            "Period days must be at least 1",
            400,
        )

    start, end = _validate_period(
        start,
        end,
        window_days,
    )

    df = _prepare_data(
        repo.get_harmonized(region_id)
    )

    if df.empty:
        raise TerraFlareError(
            "no_data",
            "No valid harmonized data is available",
            404,
        )

    daily = _daily(df)

    d0 = daily.index.min()
    d1 = daily.index.max()

    periods = []
    flagged = 0

    p_start = start

    while p_start <= end:

        p_end = min(
            p_start + pd.Timedelta(days=period_days - 1),
            end,
        )

        observed = float(
            daily["value"].loc[p_start:p_end].sum()
        )

        baseline = _baseline(
            daily["value"],
            p_start,
            p_end,
            window_days,
            d0,
            d1,
        )

        baseline_values = list(
            baseline.values()
        )

        z, percentile = _score(
            observed,
            baseline_values,
            settings.anomaly_min_baseline_years,
        )

        observed_lower = float(
            daily["lower"].loc[p_start:p_end].sum()
        )

        observed_upper = float(
            daily["upper"].loc[p_start:p_end].sum()
        )

        z_lower, _ = _score(
            observed_lower,
            baseline_values,
            settings.anomaly_min_baseline_years,
        )

        z_upper, _ = _score(
            observed_upper,
            baseline_values,
            settings.anomaly_min_baseline_years,
        )

        is_anomalous = (
            z is not None
            and z >= settings.anomaly_z_flag
        )

        flagged += int(is_anomalous)

        periods.append(
            {
                "period_start": iso(p_start),
                "period_end": iso(p_end),
                "observed": num(observed),
                "observed_lower": num(observed_lower),
                "observed_upper": num(observed_upper),
                "baseline_median": (
                    num(np.median(baseline_values))
                    if baseline_values
                    else None
                ),
                "robust_z": num(z),
                "robust_z_lower": num(z_lower),
                "robust_z_upper": num(z_upper),
                "percentile": num(percentile, 1),
                "n_baseline_years": len(baseline),
                "is_anomalous": is_anomalous,
                "is_partial": (
                    (p_end - p_start).days + 1
                    < period_days
                ),
            }
        )

        p_start = p_end + pd.Timedelta(days=1)

    notes = [
        f"Periods flagged when robust z >= {settings.anomaly_z_flag}; "
        f"at least {settings.anomaly_min_baseline_years} prior years required.",
        "Periods without enough historical baseline years are not scored.",
        "An anomaly does not identify the cause of unusual activity.",
    ]

    return {
        "periods": periods,
        "flagged_count": flagged,
        "parameters": {
            "period_days": period_days,
            "window_days": window_days,
            "z_flag": settings.anomaly_z_flag,
        },
        "notes": notes,
    }


def _top(
    series: pd.Series,
    k: int,
):
    """Return top positive contributions and their relative share."""

    positive = series[
        np.isfinite(series)
        & (series > 0)
    ].sort_values(
        ascending=False
    )

    denominator = float(
        positive.sum()
    )

    top = positive.head(k)

    if denominator <= 0:
        return [], None

    result = [
        (
            index,
            float(value),
            float(value / denominator),
        )
        for index, value in top.items()
    ]

    share = float(
        top.sum() / denominator
    )

    return result, share


def explain(
    repo,
    region_id,
    start,
    end,
    window_days,
    top_k,
) -> dict:

    start, end = _validate_period(
        start,
        end,
        window_days,
    )

    if top_k < 1:
        raise TerraFlareError(
            "invalid_top_k",
            "top_k must be at least 1",
            400,
        )

    df = _prepare_data(
        repo.get_harmonized(region_id)
    )

    if df.empty:
        raise TerraFlareError(
            "no_data",
            "No valid harmonized data is available",
            404,
        )

    daily = _daily(df)

    d0 = daily.index.min()
    d1 = daily.index.max()

    if start < d0 or end > d1:
        raise TerraFlareError(
            "period_outside_data",
            "Period must lie inside the dataset range",
            400,
        )

    period_length = (
        end - start
    ).days + 1

    observed = float(
        daily["value"].loc[start:end].sum()
    )

    windows = list(
        _windows(
            start,
            end,
            window_days,
            d0,
            d1,
        )
    )

    baseline = _baseline(
        daily["value"],
        start,
        end,
        window_days,
        d0,
        d1,
    )

    baseline_values = list(
        baseline.values()
    )

    min_years = settings.anomaly_min_baseline_years

    z, percentile = _score(
        observed,
        baseline_values,
        min_years,
    )

    median = (
        float(np.median(baseline_values))
        if baseline_values
        else None
    )

    observed_lower = float(
        daily["lower"].loc[start:end].sum()
    )

    observed_upper = float(
        daily["upper"].loc[start:end].sum()
    )

    z_lower, _ = _score(
        observed_lower,
        baseline_values,
        min_years,
    )

    z_upper, _ = _score(
        observed_upper,
        baseline_values,
        min_years,
    )

    top_dates = []
    top_cells = []

    dates_share = None
    cells_share = None

    if len(baseline) >= min_years:

        # -------------------------------------------------
        # Contribution by date
        # -------------------------------------------------

        daily_excess = {}

        for date in pd.date_range(
            start,
            end,
            freq="D",
        ):

            historical_rates = []

            for year in baseline:

                year_difference = (
                    start.year - year
                )

                historical_date = (
                    date
                    - pd.DateOffset(
                        years=year_difference
                    )
                )

                ws = (
                    historical_date
                    - pd.Timedelta(days=window_days)
                )

                we = (
                    historical_date
                    + pd.Timedelta(days=window_days)
                )

                historical_window = daily[
                    "value"
                ].loc[ws:we]

                if not historical_window.empty:
                    historical_rates.append(
                        float(historical_window.mean())
                    )

            if historical_rates:
                expected = float(
                    np.median(historical_rates)
                )
            else:
                expected = 0.0

            actual = float(
                daily["value"].loc[date]
            )

            daily_excess[date] = actual - expected

        date_contributions, dates_share = _top(
            pd.Series(daily_excess),
            top_k,
        )

        top_dates = [
            {
                "date": iso(date),
                "excess": num(excess),
                "share": num(share),
            }
            for date, excess, share in date_contributions
        ]

        # -------------------------------------------------
        # Contribution by H3 cell
        # -------------------------------------------------

        selected = df[
            (df["acq_date"] >= start)
            & (df["acq_date"] <= end)
        ]

        cell_observed = (
            selected.groupby("h3_cell")[
                "harmonized_value"
            ].sum()
        )

        baseline_columns = {}

        for year, ws, we in windows:

            historical = df[
                (df["acq_date"] >= ws)
                & (df["acq_date"] <= we)
            ]

            cell_values = (
                historical.groupby("h3_cell")[
                    "harmonized_value"
                ].sum()
            )

            window_length = (
                (we - ws).days + 1
            )

            baseline_columns[year] = (
                cell_values
                .reindex(
                    cell_observed.index,
                    fill_value=0.0,
                )
                * period_length
                / window_length
            )

        if baseline_columns:

            cell_baseline = pd.DataFrame(
                baseline_columns
            ).median(axis=1)

            cell_excess = (
                cell_observed - cell_baseline
            )

            cell_contributions, cells_share = _top(
                cell_excess,
                top_k,
            )

            top_cells = [
                {
                    "h3_cell": str(cell),
                    "excess": num(excess),
                    "share": num(share),
                }
                for cell, excess, share in cell_contributions
            ]

    # -------------------------------------------------
    # Generate human-readable explanation
    # -------------------------------------------------

    if z is None:

        explanation = (
            f"Not enough prior years ({len(baseline)}, "
            f"need {min_years}) to score this period. "
            f"Observed harmonized activity: {observed:.1f}."
        )

    else:

        ratio = (
            observed / median
            if median is not None and median > 0
            else None
        )

        if ratio is not None:

            heading = (
                f"Activity in the selected period was "
                f"{ratio:.1f} times the baseline median "
                f"({observed:.1f} vs {median:.1f})"
            )

        else:

            heading = (
                f"Activity was {observed:.1f}; "
                f"the baseline median was zero"
            )

        explanation = (
            f"{heading}, based on {len(baseline)} prior years "
            f"(robust z = {z:.1f}, percentile {percentile:.0f})."
        )

        if top_cells and top_dates:

            explanation += (
                f" {len(top_cells)} cells account for "
                f"{cells_share:.0%} of the positive excess, "
                f"mostly on "
                f"{', '.join(item['date'] for item in top_dates[:3])}."
            )

        explanation += (
            " This describes the record only and does not state a cause."
        )

    return {
        "period": {
            "start": iso(start),
            "end": iso(end),
        },
        "score": {
            "observed": num(observed),
            "baseline_median": num(median),
            "ratio_to_median": (
                num(observed / median)
                if median is not None and median > 0
                else None
            ),
            "robust_z": num(z),
            "robust_z_lower": num(z_lower),
            "robust_z_upper": num(z_upper),
            "percentile": num(percentile, 1),
            "n_baseline_years": len(baseline),
            "baseline_years": sorted(baseline),
        },
        "top_dates": top_dates,
        "top_cells": top_cells,
        "top_dates_share": num(dates_share),
        "top_cells_share": num(cells_share),
        "explanation": explanation,
        "notes": [
            "Harmonization uncertainty is shown as robust_z_lower / robust_z_upper.",
            "Anomaly scores describe unusual recorded activity, not its cause.",
            "Contribution shares represent positive excess only.",
        ],
    }
