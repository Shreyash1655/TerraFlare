from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.core.dependencies import RepoDep
from app.schemas.common import Envelope
from app.schemas.quality import ProvenanceData, QualityData
from app.services import quality_service as svc
from app.utils.params import resolve_range
from app.utils.response import make_envelope

router = APIRouter(tags=["Quality"])


@router.get("", response_model=Envelope[QualityData])
def get_quality(
    repo: RepoDep,
    region_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    sensors: str | None = None,
):
    s, e = resolve_range(repo, start, end, default_days=365)
    sens = [x.strip() for x in sensors.split(",") if x.strip()] if sensors else None
    data = svc.compute_quality(repo, region_id, s, e, sens)
    return make_envelope(repo, data, dict(region_id=region_id, start=s.date(), end=e.date(), sensors=sensors), svc.LIMITATIONS)


@router.get("/provenance", response_model=Envelope[ProvenanceData])
def get_provenance(repo: RepoDep):
    return make_envelope(repo, svc.provenance(repo), {}, ["Provenance comes from ingest_log written by the core pipeline."])