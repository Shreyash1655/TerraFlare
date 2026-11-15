"""Core endpoints (/regions, /calendar, /history/*) computed from the repository's obs_clean table.
One dataset at a time: daily values are never summed across sensors/products.
/calendar prefers the harmonized mart + coverage_day (NOAA-20 VIIRS counts)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter
from app.core.dependencies import RepoDep
from app.utils.errors import TerraFlareError
from app.utils.response import make_envelope

router = APIRouter(tags=["Core"])
DEFAULT_DATASET = "J1_VIIRS_C2_Global_48h"
NAMES = {"global": "India (ingested FIRMS data)", "goa": "Goa (synthetic fixture)"}
LIMITS = [
    "Values are the daily sum of fire radiative power (MW) for ONE satellite product; they are not a harmonized index.",
    "Detections are not unique fires and are never merged across sensors or products.",
    "NRT products are near real-time and not standard science-quality historical data; first/last days of a window may be partial.",
    "No multi-year baseline or uncertainty model exists for this data, so medians and intervals are null.",
]
REGION_LIMITS = [
    "The region covers only H3 res-5 cells that contain at least one standard-processing (SP) detection; the bbox is the extent of the ingested rows, not an administrative boundary.",
    "The data combine SP (historical) and NRT (provisional) streams; they are kept separate by processing stream.",
    "Hotspots are thermal anomalies, not unique fires. MODIS and VIIRS counts are never added.",
    "Absence of hotspots does not imply coverage or absence of fire; coverage comes from ingested file ranges.",
]
CALENDAR_LIMITS = [
    "Daily values are NOAA-20 VIIRS detections (thermal anomalies, not unique fires) over the ingested India footprint; MODIS is not added.",
    "Dates are local solar dates, as in the harmonized mart. The region selector does not subset this view.",
    "Coverage comes from ingested file ranges, never from detection counts. Uncovered, partial-edge and suspect-zero days are shown as no data, not zero.",
    "Days marked provisional come from the NRT stream and are not science-quality. No multi-year baseline exists, so no median or interval is shown.",
]
_cache: dict = {}


def _load(repo):
    k = id(repo)
    if k not in _cache:
        o = repo.get_observations()
        if "source_dataset" not in o.columns:
            o = o.assign(source_dataset="all")
        daily = (o.groupby(["region_id", "source_dataset", "acq_date"])
                 .agg(frp_sum=("frp_mw", "sum"), n=("frp_mw", "size")).reset_index())
        win = o.groupby(["region_id", "source_dataset"])["acq_datetime_utc"].agg(["min", "max"]).reset_index()
        bbox = o.groupby("region_id").agg(x0=("lon", "min"), y0=("lat", "min"), x1=("lon", "max"), y1=("lat", "max")).reset_index()
        _cache[k] = (daily, win, bbox)
    return _cache[k]


def _select(repo, region_id, dataset):
    daily, win, bbox = _load(repo)
    regions = sorted(daily["region_id"].unique())
    if not regions:
        raise TerraFlareError("no_data", "No observations available", 404)
    rid = region_id or regions[0]
    if rid not in regions:
        raise TerraFlareError("region_not_found", f"Unknown region_id '{rid}'", 404)
    avail = sorted(daily.loc[daily.region_id == rid, "source_dataset"].unique())
    ds = dataset or (DEFAULT_DATASET if DEFAULT_DATASET in avail else avail[0])
    if ds not in avail:
        raise TerraFlareError("dataset_not_found", f"Unknown dataset '{ds}'", 404, {"available": avail})
    d = daily[(daily.region_id == rid) & (daily.source_dataset == ds)].sort_values("acq_date")
    w = win[(win.region_id == rid) & (win.source_dataset == ds)].iloc[0]
    return rid, ds, d, w


def _unit(repo, ds):
    return f"FRP sum (MW) - {'NRT, ' if not repo.is_synthetic else 'synthetic, '}{ds}"


def _flag(date, w):
    first, last = pd.Timestamp(w["min"]), pd.Timestamp(w["max"])
    if date == last.normalize() and last.hour < 20:
        return "low_coverage"
    if date == first.normalize() and first.hour >= 1:
        return "low_coverage"
    return "normal"


def _mart_calendar(repo, year):
    """Daily NOAA-20 VIIRS counts from the mart, gated by coverage_day. None if unavailable."""
    if getattr(repo, "is_synthetic", False):
        return None
    base = Path(repo.data_dir) / "marts"
    hp, cp = base / "harmonized_cell_day.parquet", base / "coverage_day.parquet"
    if not (hp.exists() and cp.exists()):
        return None
    if "mart" not in _cache:
        h = pd.read_parquet(hp, columns=["acq_date", "viirs_observed", "is_provisional"])
        h["acq_date"] = pd.to_datetime(h["acq_date"]).dt.normalize()
        h["is_provisional"] = h["is_provisional"].fillna(False).astype(bool)
        d = h.groupby("acq_date").agg(v=("viirs_observed", "sum"), prov=("is_provisional", "max"))
        c = pd.read_parquet(cp)
        c["acq_date"] = pd.to_datetime(c["acq_date"]).dt.normalize()
        for col in ("viirs_covered", "viirs_suspect_zero"):
            c[col] = c[col].fillna(False).astype(bool)
        _cache["mart"] = (d, c)
    d, c = _cache["mart"]
    years = sorted({int(y) for y in c.loc[c["viirs_covered"], "acq_date"].dt.year.unique()})
    if not years:
        return None
    y = year if year in years else years[-1]
    days = []
    for r in c[c["acq_date"].dt.year == y].sort_values("acq_date").itertuples():
        has = r.acq_date in d.index
        v = float(d.at[r.acq_date, "v"]) if has else None
        prov = bool(d.at[r.acq_date, "prov"]) if has else False
        if r.viirs_suspect_zero:
            val, flag, why = None, "suspect_zero", "In file range but zero detections; treated as missing"
        elif not r.viirs_covered:
            val, flag = None, ("low_coverage" if has else "no_data")
            why = "Partial edge day of a file" if has else "Outside every VIIRS file range"
        else:
            val, flag, why = (v if has else 0.0), "normal", ""
        days.append({"date": r.acq_date.date().isoformat(), "harmonized_value": val, "lower": None,
                     "upper": None, "data_flag": flag, "reason": why, "is_provisional": prov})
    return {"year": y, "available_years": years, "days": days,
            "unit": "NOAA-20 VIIRS detections per day (thermal anomalies, not unique fires)",
            "dataset": "harmonized_cell_day + coverage_day"}


@router.get("/regions")
def regions(repo: RepoDep):
    daily, _, bbox = _load(repo)
    items = [{"region_id": r.region_id, "name": NAMES.get(r.region_id, r.region_id),
              "bbox": [round(r.x0, 4), round(r.y0, 4), round(r.x1, 4), round(r.y1, 4)]} for r in bbox.itertuples()]
    return make_envelope(repo, {"regions": items}, None, REGION_LIMITS)


@router.get("/calendar")
def calendar(repo: RepoDep, region_id: str | None = None, year: int | None = None, dataset: str | None = None):
    if dataset is None:
        m = _mart_calendar(repo, year)
        if m is not None:
            return make_envelope(repo, m, {"region_id": region_id, "year": m["year"]}, CALENDAR_LIMITS)
    rid, ds, d, w = _select(repo, region_id, dataset)
    if year is not None:
        d = d[d.acq_date.dt.year == year]
    days = [{"date": r.acq_date.date().isoformat(), "harmonized_value": round(float(r.frp_sum), 2),
             "lower": None, "upper": None, "data_flag": _flag(r.acq_date, w), "detections": int(r.n)}for r in d.itertuples()]
    return make_envelope(repo, {"year": year, "unit": _unit(repo, ds), "dataset": ds, "days": days},
                         {"region_id": rid, "year": year, "dataset": ds}, LIMITS)


@router.get("/history/yearly")
def history_yearly(repo: RepoDep, region_id: str | None = None, dataset: str | None = None):
    rid, ds, d, _ = _select(repo, region_id, dataset)
    g = d.groupby(d.acq_date.dt.year).agg(v=("frp_sum", "sum")).reset_index()
    years = [{"year": int(r.acq_date), "harmonized_value": round(float(r.v), 2), "lower": None, "upper": None,
              "modis_observed": None, "viirs_observed": None, "sensor_mix": [ds]} for r in g.itertuples()]
    return make_envelope(repo, {"years": years}, {"region_id": rid, "dataset": ds}, LIMITS)


@router.get("/history/monthly")
def history_monthly(repo: RepoDep, region_id: str | None = None, dataset: str | None = None):
    rid, ds, d, w = _select(repo, region_id, dataset)
    last = pd.Timestamp(w["max"])
    g = d.groupby([d.acq_date.dt.year.rename("y"), d.acq_date.dt.month.rename("m")]).agg(v=("frp_sum", "sum")).reset_index()
    matrix = [{"year": int(r.y), "month": int(r.m), "harmonized_value": round(float(r.v), 2), "lower": None, "upper": None,
               "is_partial": bool((r.y, r.m) == (last.year, last.month) and last.day < last.days_in_month)} for r in g.itertuples()]
    return make_envelope(repo, {"matrix": matrix}, {"region_id": rid, "dataset": dataset or ds}, LIMITS)


@router.get("/history/current-vs-median")
def current_vs_median(repo: RepoDep, region_id: str | None = None, month: int | None = None, dataset:str | None = None):
    rid, ds, d, w = _select(repo, region_id, dataset)
    last = pd.Timestamp(w["max"])
    m = month or last.month
    cur = d[(d.acq_date.dt.year == last.year) & (d.acq_date.dt.month == m)]["frp_sum"].sum()
    data = {"year": int(last.year), "month": int(m), "is_partial": bool(last.day < last.days_in_month),
            "current": round(float(cur), 2), "median": None, "q25": None, "q75": None,
            "n_baseline_years": 0, "ratio_to_median": None}
    return make_envelope(repo, data, {"region_id": rid, "month": m, "dataset": ds}, LIMITS)