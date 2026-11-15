"""Map endpoints: /hotspots (GeoJSON points) and /hotspots/cells (H3 counts) from the repository's obs_clean table.
Detections are never merged into unique fires or harmonized across sensors."""
from __future__ import annotations

import h3
import pandas as pd
from fastapi import APIRouter, Query
from app.core.dependencies import RepoDep
from app.utils.errors import TerraFlareError
from app.utils.response import make_envelope

router = APIRouter(tags=["Hotspots"])
DEFAULT_WINDOW_DAYS = 30
BASE_LIMITS = [
    "Hotspots are satellite thermal-anomaly detections, not confirmed unique fires; nothing is de-duplicated across sensors or platforms.",
    "Cell-level harmonized values are not produced: in the VIIRS era the harmonized series equals the NOAA-20 observation (no MODIS conversion), so harmonized_value, lower and upper are null here.",
    "Counts are detections only; sensor coverage is not evaluated here, so a zero is not proof of no fire.",
]
MODE_LIMITS = {
    "NRT": "NRT products are near real-time and not standard science-quality historical data.",
    "SP": "Standard-processing (science-quality) data.",
    "MIXED": "This window mixes NRT (provisional) and standard-processing data.",
}
_cell_cache: dict = {}


def _obs(repo, region_id, start, end, exclude_noaa21=False):
    o = repo.get_observations()
    regions = sorted(o["region_id"].unique())
    if not regions:
        raise TerraFlareError("no_data", "No observations available", 404)
    rid = region_id or regions[0]
    if rid not in regions:
        raise TerraFlareError("region_not_found", f"Unknown region_id '{rid}'", 404)
    o = o[o["region_id"] == rid]
    if exclude_noaa21 and "source_dataset" in o.columns:
        # single VIIRS reference platform (NOAA-20): NOAA-21 detections would double-count the same fires
        o = o[~o["source_dataset"].astype(str).str.upper().str.startswith("J2_VIIRS")]
    if start or end:
        if start:
            o = o[o["acq_datetime_utc"] >= pd.Timestamp(start)]
        if end:
            if len(str(end)) <= 10:  # a plain date means "through the end of that day"
                o = o[o["acq_datetime_utc"] <= pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
            else:
                o = o[o["acq_datetime_utc"] <= pd.Timestamp(end)]
        window = {"start": start, "end": end, "basis": "requested"}
    elif o.empty:
        window = {"start": None, "end": None, "basis": f"latest {DEFAULT_WINDOW_DAYS} days of data"}
    else:
        we = o["acq_datetime_utc"].max()
        ws = we - pd.Timedelta(days=DEFAULT_WINDOW_DAYS)
        o = o[o["acq_datetime_utc"] >= ws]
        window = {"start": ws.isoformat(), "end": we.isoformat(), "basis": f"latest {DEFAULT_WINDOW_DAYS} days of data"}
    return rid, o, window


def _mode(o):
    if o.empty or "product_type" not in o.columns:
        return None
    t = sorted(o["product_type"].dropna().astype(str).str.upper().unique())
    if not t:
        return None
    return t[0] if len(t) == 1 else "MIXED"


def _limits(mode):
    return BASE_LIMITS + [MODE_LIMITS.get(mode, "Processing mode (NRT or standard) is not available in the source data.")]


def _sensor_list(sensors):
    if sensors is None:
        return None
    return [s.strip().upper() for s in sensors.split(",") if s.strip()]


@router.get("/hotspots")
def hotspots(repo: RepoDep, region_id: str | None = None, start: str | None = None, end: str | None = None,
             sensors: str | None = None, min_confidence: str | None = None,
             limit: int = Query(5000, ge=1, le=50000)):
    rid, o, window = _obs(repo, region_id, start, end)
    want = _sensor_list(sensors)
    if want is not None:
        o = o[o["sensor_family"].str.upper().isin(want)]
    if min_confidence:
        order = {"low": 0, "medium": 1, "nominal": 1, "high": 2}
        o = o[o["confidence_class"].map(order).fillna(-1) >= order.get(min_confidence.lower(), 0)]
    total = len(o)
    mode = _mode(o)
    fams = sorted(o["sensor_family"].unique())
    # fair truncation: equal share per sensor family, highest FRP first (deterministic)
    parts = [g.nlargest(max(1, limit // max(1, len(fams))), "frp_mw") for _, g in o.groupby("sensor_family")]
    sel = pd.concat(parts) if parts else o.head(0)
    feats = []
    for r in sel.itertuples():
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(float(r.lon), 5), round(float(r.lat), 5)]},
                      "properties": {"obs_id": r.record_id if hasattr(r, "record_id") else None, "sensor_family": r.sensor_family,
                                     "platform": r.platform, "acq_datetime_utc": pd.Timestamp(r.acq_datetime_utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "confidence_class": r.confidence_class, "confidence_raw": r.confidence_raw,
                                     "frp_mw": float(r.frp_mw), "source_dataset": getattr(r, "source_dataset", None),
                                     "product_type": getattr(r, "product_type", None)}})
    data = {"type": "FeatureCollection", "truncated": bool(total > len(feats)), "total_matching": int(total),
            "window": window, "processing_mode": mode, "features": feats}
    lim = _limits(mode) + (["Result truncated: equal share per sensor family, highest FRP first."] if data["truncated"] else [])
    return make_envelope(repo, data, {"region_id": rid, "start": start, "end": end, "sensors": sensors, "limit": limit}, lim)


def _cells_for(repo, o, res):
    key = (id(repo), res)
    if key not in _cell_cache:
        full = repo.get_observations()
        ll = full[["lat", "lon"]].drop_duplicates()
        _cell_cache[key] = {(a, b): h3.latlng_to_cell(a, b, res) for a, b in zip(ll.lat, ll.lon)}
    m = _cell_cache[key]
    return pd.Series([m[(a, b)] for a, b in zip(o.lat, o.lon)], index=o.index)


@router.get("/hotspots/cells")
def hotspot_cells(repo: RepoDep, region_id: str | None = None, start: str | None = None, end: str | None = None,
                  h3_res: int = Query(7, ge=1, le=10), limit: int = Query(500, ge=1, le=5000)):
    # NOAA-21 excluded: one VIIRS reference platform (NOAA-20), never summed with another VIIRS platform
    rid, o, window = _obs(repo, region_id, start, end, exclude_noaa21=True)
    mode = _mode(o)
    o = o.assign(cell=_cells_for(repo, o, h3_res))
    fam = o["sensor_family"].str.upper()
    g = o.assign(modis=(fam == "MODIS").astype(int), viirs=(fam == "VIIRS").astype(int),
                 frp_modis=o["frp_mw"].where(fam == "MODIS", 0.0), frp_viirs=o["frp_mw"].where(fam == "VIIRS", 0.0)
                 ).groupby("cell").agg(modis_observed=("modis", "sum"), viirs_observed=("viirs", "sum"),
                                       frp_sum_modis=("frp_modis", "sum"), frp_sum_viirs=("frp_viirs", "sum")).reset_index()
    g["tot"] = g.modis_observed + g.viirs_observed
    total_cells = len(g)
    g = g.sort_values("tot", ascending=False).head(limit)
    cells = [{"h3_cell": r.cell, "harmonized_value": None, "lower": None, "upper": None,
              "modis_observed": int(r.modis_observed), "viirs_observed": int(r.viirs_observed),
              "frp_sum_modis": round(float(r.frp_sum_modis), 2), "frp_sum_viirs": round(float(r.frp_sum_viirs), 2)} for r in g.itertuples()]
    data = {"h3_resolution": h3_res, "truncated": bool(total_cells > len(cells)), "total_cells": int(total_cells),
            "window": window, "processing_mode": mode, "cells": cells}
    lim = _limits(mode) + ["modis_observed / viirs_observed are raw detection counts within the same time window; MODIS (1 km) and VIIRS (375 m) differ in resolution and sensitivity. VIIRS counts use NOAA-20 only."]
    return make_envelope(repo, data, {"region_id": rid, "h3_res": h3_res, "limit": limit}, lim)