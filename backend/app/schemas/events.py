from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class EventParams(BaseModel):
    eps_km: float
    time_scale_km_per_day: float
    min_samples: int


class EventSummary(BaseModel):
    event_id: str
    first_detection: datetime
    last_detection: datetime
    n_detections: int
    active_days: int
    sensors: list[str]
    n_by_sensor: dict[str, int]
    centroid: list[float]  # [lon, lat]
    footprint_geojson: dict[str, Any] | None = None
    max_frp_mw: float | None = None


class EventListData(BaseModel):
    events: list[EventSummary]
    label: str
    parameters: EventParams
    n_points_processed: int
    n_noise_points: int
    truncated: bool
    notes: list[str] = Field(default_factory=list)


class EventDay(BaseModel):
    date: date
    n_detections: int
    frp_sum_mw: float | None = None
    frp_max_mw: float | None = None


class EventDetailData(BaseModel):
    event_id: str
    summary: EventSummary
    daily: list[EventDay]
    parameters: EventParams
    label: str