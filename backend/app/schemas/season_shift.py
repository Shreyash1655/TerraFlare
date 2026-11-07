from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SeasonYear(BaseModel):
    year: int
    onset: date | None = None
    peak: date | None = None
    end: date | None = None
    length_days: int | None = None
    onset_doy: int | None = None
    peak_doy: int | None = None
    end_doy: int | None = None
    total_activity: float
    sensor_mix: list[str] = Field(default_factory=list)
    is_partial: bool = False
    status: Literal["ok", "partial", "insufficient_activity"]


class ShiftEstimate(BaseModel):
    estimate: float | None = None
    ci: list[float | None] = Field(default_factory=lambda: [None, None])


class SeasonComparison(BaseModel):
    baseline: list[int] = Field(default_factory=list)
    recent: list[int] = Field(default_factory=list)
    n_baseline_years: int = 0
    n_recent_years: int = 0
    onset_shift_days: ShiftEstimate = Field(default_factory=ShiftEstimate)
    end_shift_days: ShiftEstimate = Field(default_factory=ShiftEstimate)
    peak_shift_days: ShiftEstimate = Field(default_factory=ShiftEstimate)
    peak_month_change: int | None = None
    evidence: Literal["insufficient_evidence", "interval_excludes_zero"] = "insufficient_evidence"


class SeasonTrend(BaseModel):
    n_years: int = 0
    onset_slope_days_per_year: float | None = None
    onset_p_value: float | None = None
    end_slope_days_per_year: float | None = None
    end_p_value: float | None = None


class SeasonParams(BaseModel):
    smooth_days: int
    onset_pct: float
    end_pct: float
    ci_level: float
    bootstrap_n: int


class SeasonShiftData(BaseModel):
    years: list[SeasonYear]
    comparison: SeasonComparison
    trend: SeasonTrend
    parameters: SeasonParams
    notes: list[str] = Field(default_factory=list)