from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import RepoDep
from app.services import short_window_service as svc
from app.utils.response import make_envelope

router = APIRouter(tags=["Short window"])


@router.get("/anomalies")
def sw_anomalies(repo: RepoDep, sensor: str = Query("viirs", pattern="^(viirs|modis)$")):
    return make_envelope(repo, svc.anomalies(repo._table("obs_clean"), sensor),
                         dict(sensor=sensor), svc.LIMITATIONS)


@router.get("/persistence")
def sw_persistence(repo: RepoDep, sensor: str = Query("viirs", pattern="^(viirs|modis)$"),
                   limit: int = Query(500, ge=1, le=5000)):
    return make_envelope(repo, svc.persistence(repo._table("obs_clean"), sensor, limit),
                         dict(sensor=sensor, limit=limit), svc.LIMITATIONS)