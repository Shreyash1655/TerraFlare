from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.dependencies import RepoDep
from app.schemas.common import Envelope
from app.schemas.season_shift import SeasonShiftData
from app.services import season_shift_service as svc
from app.utils.errors import TerraFlareError
from app.utils.response import make_envelope

router = APIRouter(tags=["Season shift"])


@router.get("", response_model=Envelope[SeasonShiftData])
def get_season_shift(
    repo: RepoDep,
    region_id: str | None = None,
    baseline_start: int | None = None,
    baseline_end: int | None = None,
    recent_start: int | None = None,
    recent_end: int | None = None,
    onset_pct: float = Query(settings.season_onset_pct, gt=0, lt=100),
    end_pct: float = Query(settings.season_end_pct, gt=0, lt=100),
):
    if onset_pct >= end_pct:
        raise TerraFlareError("invalid_threshold", "onset_pct must be smaller than end_pct", 400)
    data = svc.compute_season_shift(repo, region_id, baseline_start, baseline_end, recent_start, recent_end, onset_pct, end_pct)
    params = dict(region_id=region_id, baseline_start=baseline_start, baseline_end=baseline_end,
                  recent_start=recent_start, recent_end=recent_end, onset_pct=onset_pct, end_pct=end_pct)
    return make_envelope(repo, data, params, svc.LIMITATIONS)