from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    api_version: str
    data_version: str
    data_mode: str
    is_synthetic: bool
    method_id: str | None = None
    generated_at: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class Envelope(BaseModel, Generic[T]):
    meta: Meta
    data: T


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


class DateRange(BaseModel):
    start: date
    end: date