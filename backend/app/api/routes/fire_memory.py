from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.dependencies import RepoDep
from app.schemas.common import Envelope
from app.schemas.fire_memory import CellTimelineData, FireMemoryCellsData, MemoryClass
from app.services import fire_memory_service as svc
from app.utils.response import make_envelope

router = APIRouter(tags=["Fire memory"])


@router.get("/cells", response_model=Envelope[FireMemoryCellsData])
def get_cells(
    repo: RepoDep,
    region_id: str | None = None,
    memory_class: MemoryClass | None = Query(None, alias="class"),
    min_activity: float = Query(settings.memory_min_activity, ge=0),
    limit: int = Query(settings.default_limit, ge=1, le=settings.max_limit),
):
    data = svc.compute_cells(repo, region_id, memory_class, min_activity, limit)
    params = dict(region_id=region_id, memory_class=memory_class, min_activity=min_activity, limit=limit)
    return make_envelope(repo, data, params, svc.LIMITATIONS)


@router.get("/cells/{h3_id}/timeline", response_model=Envelope[CellTimelineData])
def get_timeline(h3_id: str, repo: RepoDep, region_id: str | None = None):
    return make_envelope(repo, svc.cell_timeline(repo, h3_id, region_id), dict(region_id=region_id, h3_id=h3_id), svc.LIMITATIONS)