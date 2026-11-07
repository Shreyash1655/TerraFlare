from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.dependencies import RepoDep
from app.schemas.anomalies import AnomalyExplainData, AnomalyListData
from app.schemas.common import Envelope
from app.services import anomaly_service as svc
from app.utils.params import resolve_range
from app.utils.response import make_envelope

router = APIRouter(tags=["Anomalies"])


@router.get("", response_model=Envelope[AnomalyListData])
def get_anomalies(
    repo: RepoDep,
    region_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    period_days: int = Query(settings.anomaly_period_days, ge=1, le=31),
    window_days: int = Query(settings.anomaly_window_days, ge=0, le=30),
):
    s, e = resolve_range(repo, start, end, default_days=365)
    data = svc.list_anomalies(repo, region_id, s, e, period_days, window_days)
    return make_envelope(repo, data, dict(region_id=region_id, start=s.date(), end=e.date(),
                                          period_days=period_days, window_days=window_days), svc.LIMITATIONS)


@router.get("/explain", response_model=Envelope[AnomalyExplainData])
def explain_anomaly(
    repo: RepoDep,
    start: date,
    end: date,
    region_id: str | None = None,
    window_days: int = Query(settings.anomaly_window_days, ge=0, le=30),
    top_k: int = Query(settings.anomaly_top_k, ge=1, le=50),
):
    s, e = resolve_range(repo, start, end, max_days=settings.anomaly_max_explain_days)
    data = svc.explain(repo, region_id, s, e, window_days, top_k)
    return make_envelope(repo, data, dict(region_id=region_id, start=s.date(), end=e.date(),
                                          window_days=window_days, top_k=top_k), svc.LIMITATIONS)