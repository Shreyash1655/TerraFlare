"""Feature 1 - Fire Season Shift Detector (descriptive, never causal)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import settings
from app.utils.response import iso, num
from app.utils.stats import bootstrap_median_diff, theil_sen


# Assumption (documented in notes): a year with more missing days than this
# is treated as partial and excluded from comparison and trend.
MAX_MISSING_DAYS = 14

LIMITATIONS = [
    "Descriptive only: no claim about climate or other causes.",
    "Timing uses the distribution of harmonized activity (NOAA-20 VIIRS series), not single detections.",
    "Days without coverage are missing, not zero; years with many missing days are marked partial and excluded.",
    "A change in sensor mix or detection practice can mimic a shift; check the sensor_mix per year.",
    "A few seasons give coarse bootstrap intervals. 'insufficient_evidence' is the default label.",
]


def _params(onset_pct, end_pct) -> dict:
    return {
        "smooth_days": settings.season_smooth_days,
        "onset_pct": onset_pct,
        "end_pct": end_pct,
        "ci_level": settings.season_ci_level,
        "bootstrap_n": settings.season_bootstrap_n,
    }


def _empty(onset_pct, end_pct, note: str) -> dict:
    return {
        "years": [],
        "comparison": {"baseline": [], "recent": [], "evidence": "insufficient_evidence"},
        "trend": {"n_years": 0},
        "parameters": _params(onset_pct, end_pct),
        "notes": [note],
    }


def _coverage_ok(repo) -> pd.Series | None:
    """Bool series (index = date): VIIRS covered and not suspect-zero. None if unavailable."""
    try:
        p = Path(repo.data_dir) / "marts" / "coverage_day.parquet"
        if not p.exists():
            return None
        c = pd.read_parquet(p, columns=["acq_date", "viirs_covered", "viirs_suspect_zero"])
        c["acq_date"] = pd.to_datetime(c["acq_date"]).dt.normalize()
        ok = c["viirs_covered"].fillna(False).astype(bool) & ~c["viirs_suspect_zero"].fillna(False).astype(bool)
        return pd.Series(ok.values, index=c["acq_date"].values).groupby(level=0).max()
    except Exception:
        return None


def _daily_series(df: pd.DataFrame, cov_ok: pd.Series | None) -> pd.Series:
    """Daily harmonized values. Missing days are NaN; never filled with 0 unless covered."""
    if df.empty or "acq_date" not in df.columns:
        return pd.Series(dtype=float)

    s = df.groupby("acq_date")["harmonized_value"].sum(min_count=1)
    if s.empty:
        return pd.Series(dtype=float)

    s.index = pd.to_datetime(s.index)
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))  # NaN where absent

    if cov_ok is not None:
        cov_ok = cov_ok.copy()
        cov_ok.index = pd.to_datetime(cov_ok.index)
        ok = cov_ok.reindex(s.index).fillna(False).astype(bool)
        # Covered, non-suspect day with no detections = a real zero.
        s = s.where(~(ok & s.isna()), 0.0)
        # Suspect-zero days are missing even if a value exists.
        suspect_or_uncovered = ~ok
        s = s.where(~(suspect_or_uncovered & (s == 0.0)), np.nan)
    return s


def _sensor_mix(df_year: pd.DataFrame) -> list[str]:
    # The harmonized series is the NOAA-20 VIIRS observation; MODIS is never added.
    if "viirs_observed" in df_year.columns and (df_year["viirs_observed"].fillna(0) > 0).any():
        return ["VIIRS (NOAA-20)"]
    return []


def _year_row(year, smoothed, daily, df_year, onset_pct, end_pct, d0, d1) -> dict:
    s = smoothed[smoothed.index.year == year]
    raw = daily[daily.index.year == year]
    total = float(s.sum())  # NaN skipped

    year_start = pd.Timestamp(year=year, month=1, day=1)
    year_end = pd.Timestamp(year=year, month=12, day=31)

    n_missing = int(raw.isna().sum())
    edge_partial = d0 > year_start or d1 < year_end
    gap_partial = n_missing > MAX_MISSING_DAYS
    partial = edge_partial or gap_partial

    row = {
        "year": int(year),
        "total_activity": num(total),
        "sensor_mix": _sensor_mix(df_year),
        "is_partial": bool(partial),
        "missing_days": n_missing,
    }

    if s.empty or total < settings.season_min_total_activity:
        return {**row, "status": "insufficient_activity"}

    cum = s.fillna(0.0).cumsum() / total

    onset = (cum >= onset_pct / 100).idxmax()
    end = (cum >= end_pct / 100).idxmax()
    peak = s.idxmax()

    row.update(
        onset=iso(onset),
        peak=iso(peak),
        end=iso(end),
        onset_doy=int(onset.day_of_year),
        peak_doy=int(peak.day_of_year),
        end_doy=int(end.day_of_year),
        length_days=int((end - onset).days),
        status="partial" if partial else "ok",
    )
    return row


def _shift(a, b) -> dict:
    if (
        len(a) < settings.season_min_years_per_period
        or len(b) < settings.season_min_years_per_period
    ):
        return {"estimate": None, "ci": [None, None]}

    est, lo, hi = bootstrap_median_diff(
        a, b, settings.season_bootstrap_n, settings.random_seed, settings.season_ci_level,
    )
    return {"estimate": num(est, 2), "ci": [num(lo, 2), num(hi, 2)]}


def _month_of_doy(doy: float) -> int:
    day = max(1, min(int(round(doy)), 365))
    return int((pd.Timestamp("2001-01-01") + pd.Timedelta(days=day - 1)).month)


def compute_season_shift(
    repo,
    region_id,
    baseline_start,
    baseline_end,
    recent_start,
    recent_end,
    onset_pct,
    end_pct,
) -> dict:

    df = repo.get_harmonized(region_id)

    missing = {"acq_date", "harmonized_value"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing required harmonized columns: {sorted(missing)}")

    notes: list[str] = []

    if df.empty:
        return _empty(onset_pct, end_pct, "No harmonized activity data is available.")

    df = df.copy()
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce").dt.normalize()
    df["harmonized_value"] = pd.to_numeric(df["harmonized_value"], errors="coerce")  # NaN kept
    df = df.dropna(subset=["acq_date"])

    if df.empty:
        return _empty(onset_pct, end_pct, "No valid acquisition dates are available.")

    cov_ok = _coverage_ok(repo)
    if cov_ok is None:
        notes.append(
            "Coverage table unavailable: days without data rows are treated as missing, not zero."
        )

    daily = _daily_series(df, cov_ok)

    if daily.empty or daily.notna().sum() == 0:
        return _empty(onset_pct, end_pct, "Daily activity series could not be generated.")

    smoothed = daily.rolling(settings.season_smooth_days, center=True, min_periods=1).mean()
    smoothed = smoothed.where(daily.notna())  # never smooth values into gaps

    d0 = daily.index.min()
    d1 = daily.index.max()

    years = sorted(set(daily.index.year))
    by_year = {year: group for year, group in df.groupby(df["acq_date"].dt.year)}

    rows = [
        _year_row(year, smoothed, daily, by_year.get(year, df.iloc[0:0]), onset_pct, end_pct, d0, d1)
        for year in years
    ]

    usable = [row for row in rows if row["status"] == "ok"]
    usable_years = [row["year"] for row in usable]

    if usable_years:
        baseline_count = min(settings.season_baseline_n_years, len(usable_years))
        recent_count = min(settings.season_recent_n_years, len(usable_years))
        b0 = usable_years[0]
        b1 = usable_years[baseline_count - 1]
        r0 = usable_years[-recent_count]
        r1 = usable_years[-1]
    else:
        b0 = b1 = r0 = r1 = None

    b0 = baseline_start if baseline_start is not None else b0
    b1 = baseline_end if baseline_end is not None else b1
    r0 = recent_start if recent_start is not None else r0
    r1 = recent_end if recent_end is not None else r1

    comparison = {"baseline": [], "recent": [], "evidence": "insufficient_evidence"}

    if None not in (b0, b1, r0, r1):

        if b0 > b1 or r0 > r1:
            raise ValueError("Invalid comparison period: start year must not exceed end year.")

        base = [row for row in usable if b0 <= row["year"] <= b1]
        rec = [row for row in usable if r0 <= row["year"] <= r1]

        shifts = {
            key: _shift(
                [row[f"{key}_doy"] for row in base],
                [row[f"{key}_doy"] for row in rec],
            )
            for key in ("onset", "end", "peak")
        }

        overlap = not (b1 < r0 or r1 < b0)

        onset_ci = shifts["onset"]["ci"]
        end_ci = shifts["end"]["ci"]

        onset_supported = (
            onset_ci[0] is not None and onset_ci[1] is not None
            and (onset_ci[0] > 0 or onset_ci[1] < 0)
        )
        end_supported = (
            end_ci[0] is not None and end_ci[1] is not None
            and (end_ci[0] > 0 or end_ci[1] < 0)
        )

        evidence = (
            "interval_excludes_zero"
            if (onset_supported and end_supported and not overlap)
            else "insufficient_evidence"
        )

        peak_change = None

        if base and rec:
            baseline_peak = np.median([row["peak_doy"] for row in base])
            recent_peak = np.median([row["peak_doy"] for row in rec])
            peak_change = _month_of_doy(recent_peak) - _month_of_doy(baseline_peak)

            base_sensor_mix = {tuple(row["sensor_mix"]) for row in base}
            recent_sensor_mix = {tuple(row["sensor_mix"]) for row in rec}

            if base_sensor_mix != recent_sensor_mix:
                notes.append(
                    "Sensor mix differs between baseline and recent periods; "
                    "a shift may reflect the instruments."
                )

        if overlap:
            notes.append(
                "Baseline and recent periods overlap; evidence is labelled insufficient."
            )

        comparison = {
            "baseline": [int(b0), int(b1)],
            "recent": [int(r0), int(r1)],
            "n_baseline_years": len(base),
            "n_recent_years": len(rec),
            "onset_shift_days": shifts["onset"],
            "end_shift_days": shifts["end"],
            "peak_shift_days": shifts["peak"],
            "peak_month_change": peak_change,
            "evidence": evidence,
        }

    else:
        notes.append("Not enough complete years with activity to compare periods.")

    trend = {"n_years": len(usable)}

    if len(usable) >= 4:
        onset_slope, onset_p = theil_sen(usable_years, [row["onset_doy"] for row in usable])
        end_slope, end_p = theil_sen(usable_years, [row["end_doy"] for row in usable])
        trend.update(
            onset_slope_days_per_year=num(onset_slope),
            onset_p_value=num(onset_p),
            end_slope_days_per_year=num(end_slope),
            end_p_value=num(end_p),
        )

    if usable:
        median_onset = np.median([row["onset_doy"] for row in usable])
        median_end = np.median([row["end_doy"] for row in usable])
        if median_onset < 30 or median_end > 335:
            notes.append(
                "Season touches the calendar-year boundary; "
                "onset/end may be unreliable (wrapping seasons not handled)."
            )

    if len(usable_years) < len(rows):
        notes.append(
            "Partial years (edge of record, or more than "
            f"{MAX_MISSING_DAYS} missing days) and years without enough activity are listed "
            "but excluded from comparison and trend."
        )

    return {
        "years": rows,
        "comparison": comparison,
        "trend": trend,
        "parameters": _params(onset_pct, end_pct),
        "notes": notes,
    }