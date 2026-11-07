from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.dependencies import RepoDep
from app.schemas.common import Envelope
from app.schemas.exposure import ExposureData
from app.services import exposure_service as svc
from app.utils.params import resolve_range
from app.utils.response import make_envelope

router = APIRouter(tags=["Exposure"])


@router.get("", response_model=Envelope[ExposureData])
def get_exposure(
    repo: RepoDep,
    region_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    buffer_km: float = Query(settings.exposure_buffer_km, gt=0, le=100),
    layers: str | None = Query(None, description="comma separated layer ids; default = all available"),
):
    s, e = resolve_range(repo, start, end, default_days=30, max_days=settings.events_max_window_days)
    ids = [x.strip() for x in layers.split(",") if x.strip()] if layers else None
    data = svc.compute_exposure(repo, region_id, s, e, buffer_km, ids)
    return make_envelope(repo, data, dict(region_id=region_id, start=s.date(), end=e.date(),
                                          buffer_km=buffer_km, layers=layers), svc.LIMITATIONS)