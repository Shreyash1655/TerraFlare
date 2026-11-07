from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.dependencies import RepoDep
from app.schemas.common import Envelope
from app.schemas.events import EventDetailData, EventListData
from app.services import event_service as svc
from app.utils.params import resolve_range
from app.utils.response import make_envelope

router = APIRouter(tags=["Events"])


@router.get("", response_model=Envelope[EventListData])
def list_events(
    repo: RepoDep,
    region_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    eps_km: float = Query(settings.events_eps_km, gt=0, le=100),
    time_scale_km_per_day: float = Query(settings.events_time_scale_km_per_day, gt=0, le=100),
    min_samples: int = Query(settings.events_min_samples, ge=1, le=100),
    min_detections: int = Query(settings.events_min_detections, ge=1),
    limit: int = Query(200, ge=1, le=settings.max_limit),
):
    s, e = resolve_range(repo, start, end, settings.events_default_window_days, settings.events_max_window_days)
    data = svc.detect_events(repo, region_id, s, e, eps_km, time_scale_km_per_day, min_samples, min_detections, limit)
    params = dict(region_id=region_id, start=s.date(), end=e.date(), eps_km=eps_km,
                  time_scale_km_per_day=time_scale_km_per_day, min_samples=min_samples, min_detections=min_detections)
    return make_envelope(repo, data, params, svc.LIMITATIONS)


@router.get("/{event_id}", response_model=Envelope[EventDetailData])
def get_event(
    event_id: str,
    repo: RepoDep,
    region_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    eps_km: float = Query(settings.events_eps_km, gt=0, le=100),
    time_scale_km_per_day: float = Query(settings.events_time_scale_km_per_day, gt=0, le=100),
    min_samples: int = Query(settings.events_min_samples, ge=1, le=100),
):
    s = e = None
    if start and end:
        s, e = resolve_range(repo, start, end, max_days=settings.events_max_window_days)
    data = svc.get_event(repo, event_id, region_id, s, e, eps_km, time_scale_km_per_day, min_samples)
    return make_envelope(repo, data, dict(event_id=event_id), svc.LIMITATIONS)