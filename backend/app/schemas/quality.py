from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class SensorContribution(BaseModel):
    period: str
    sensor_family: str
    platform: str
    count: int
    share: float


class ConfidenceCount(BaseModel):
    sensor_family: str
    native_class: str
    count: int


class NormalisedConfidence(BaseModel):
    sensor_family: str
    confidence_class: str
    count: int


class AvailabilityGap(BaseModel):
    sensor_family: str
    gap_start: date
    gap_end: date
    gap_days: int
    usual_gap_days: float
    label: str


class UncertaintySummary(BaseModel):
    method_id: str | None = None
    interval_level: float | None = None
    median_relative_width: float | None = None
    validation: list[dict[str, Any]] = Field(default_factory=list)
    note: str | None = None


class QualityData(BaseModel):
    sensor_contribution: list[SensorContribution]
    confidence_distribution: list[ConfidenceCount]
    confidence_normalised: list[NormalisedConfidence]
    availability: list[AvailabilityGap]
    uncertainty_summary: UncertaintySummary
    notes: list[str] = Field(default_factory=list)


class ProvenanceRow(BaseModel):
    source_id: str | None = None
    product_version: str | None = None
    file_name: str | None = None
    sha256: str | None = None
    rows_in: int | None = None
    ingested_at: str | None = None


class ProvenanceData(BaseModel):
    sources: list[ProvenanceRow]