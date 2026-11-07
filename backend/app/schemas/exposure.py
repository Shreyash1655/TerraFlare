from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import DateRange


class ExposureLayer(BaseModel):
    layer_id: str
    source: str | None = None
    version: str | None = None
    available: bool
    count: int | None = None
    sum_value: float | None = None
    is_synthetic: bool = False


class ExposureData(BaseModel):
    period: DateRange
    buffer_km: float
    n_hotspot_locations: int
    layers: list[ExposureLayer]
    note: str
    notes: list[str] = Field(default_factory=list)