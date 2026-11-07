from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MemoryClass = Literal["persistent", "emerging", "declining", "sporadic"]


class MemoryCell(BaseModel):
    h3_cell: str
    recurrence: float
    years_active: int
    years_in_range: int
    trend_slope: float | None = None
    memory_class: MemoryClass
    total_activity: float
    first_active_year: int | None = None
    last_active_year: int | None = None


class FireMemoryCellsData(BaseModel):
    cells: list[MemoryCell]
    truncated: bool
    n_cells_total: int
    class_counts: dict[str, int]
    year_range: list[int]
    recent_window: list[int]
    notes: list[str] = Field(default_factory=list)


class AnnualPoint(BaseModel):
    year: int
    harmonized_value: float
    lower: float | None = None
    upper: float | None = None


class CellTimelineData(BaseModel):
    h3_cell: str
    annual: list[AnnualPoint]
    notes: list[str] = Field(default_factory=list)