from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import DateRange


class AnomalyPeriod(BaseModel):
    period_start: date
    period_end: date
    observed: float
    observed_lower: float | None = None
    observed_upper: float | None = None
    baseline_median: float | None = None
    robust_z: float | None = None
    robust_z_lower: float | None = None
    robust_z_upper: float | None = None
    percentile: float | None = None
    n_baseline_years: int
    is_anomalous: bool
    is_partial: bool = False


class AnomalyListData(BaseModel):
    periods: list[AnomalyPeriod]
    flagged_count: int
    parameters: dict[str, Any]
    notes: list[str] = Field(default_factory=list)


class DateContribution(BaseModel):
    date: date
    excess: float
    share: float


class CellContribution(BaseModel):
    h3_cell: str
    excess: float
    share: float


class ExplainScore(BaseModel):
    observed: float
    baseline_median: float | None = None
    ratio_to_median: float | None = None
    robust_z: float | None = None
    robust_z_lower: float | None = None
    robust_z_upper: float | None = None
    percentile: float | None = None
    n_baseline_years: int
    baseline_years: list[int] = Field(default_factory=list)


class AnomalyExplainData(BaseModel):
    period: DateRange
    score: ExplainScore
    top_dates: list[DateContribution]
    top_cells: list[CellContribution]
    top_dates_share: float | None = None
    top_cells_share: float | None = None
    explanation: str
    notes: list[str] = Field(default_factory=list)