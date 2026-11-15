from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import settings
from app.utils.errors import TerraFlareError
from app.utils.response import num

MIN_DAILY = 1000
MIN_DAYS = 14

LIMITATIONS = [
    "Short-window method: scores compare days inside the loaded window only. It is NOT a seasonal or multi-year baseline.",
    "One sensor per call; MODIS and VIIRS counts are never added together.",
    "Days with fewer than %d detections are treated as low coverage and excluded, never as zero." % MIN_DAILY,
    "Hotspot detections are thermal anomalies, not unique fires.",
]


def _prep(obs: pd.DataFrame | None, sensor: str) -> pd.DataFrame:
    if obs is None or obs.empty:
        raise TerraFlareError("no_data", "No observations available", 404)
    d = obs
    if "is_valid" in d.columns:
        d = d[d["is_valid"]]
    s = sensor.upper()
    d = d[d["sensor_family"].astype(str).str.upper() == s]
    if s == "VIIRS":
        d = d[d["platform"] == "NOAA-20"]  # single reference platform
    if d.empty:
        raise TerraFlareError("no_data", f"No {s} observations available", 404)
    col = "local_date" if "local_date" in d.columns else "acq_date"
    d = d.assign(_day=pd.to_datetime(d[col]).dt.normalize())
    return d


def _daily(d: pd.DataFrame) -> pd.Series:
    return d.groupby("_day").size().sort_index()


def anomalies(obs, sensor: str = "viirs") -> dict:
    d = _prep(obs, sensor)
    daily = _daily(d)
    ok = daily[daily >= MIN_DAILY]
    warnings = []
    excluded = [x.date().isoformat() for x in daily.index.difference(ok.index)]
    if excluded:
        warnings.append(f"{len(excluded)} low-coverage day(s) excluded.")
    base = {"method": "short_window", "sensor": sensor.upper(),
            "window": [daily.index.min().date().isoformat(), daily.index.max().date().isoformat()],
            "usable_days": int(len(ok)), "min_days": MIN_DAYS, "warnings": warnings, "days": []}
    if len(ok) < MIN_DAYS:
        warnings.append(f"Needs {MIN_DAYS} usable days; have {len(ok)}. No scores computed.")
        return base
    x = np.log1p(ok.astype(float))
    rows = []
    for day, v in x.items():
        rest = x.drop(day)  # leave-one-out baseline
        med = float(rest.median())
        mad = float((rest - med).abs().median()) * 1.4826
        z = (v - med) / mad if mad > 0 else None
        rows.append({"date": day.date().isoformat(), "count": int(ok[day]),
                     "robust_z": num(z, 2),
                     "flagged": bool(z is not None and abs(z) >= settings.anomaly_z_flag)})
    base["days"] = rows
    return base


def persistence(obs, sensor: str = "viirs", limit: int = 500) -> dict:
    d = _prep(obs, sensor)
    daily = _daily(d)
    covered = daily[daily >= MIN_DAILY].index
    warnings = []
    out = {"method": "short_window", "sensor": sensor.upper(), "covered_days": int(len(covered)),
           "min_days": MIN_DAYS, "warnings": warnings, "cells": [], "n_cells": 0, "cells_full": 0}
    if len(covered) < MIN_DAYS:
        warnings.append(f"Needs {MIN_DAYS} covered days; have {len(covered)}. No persistence computed.")
        return out
    d = d[d["_day"].isin(covered)]
    n = len(covered)
    g = (d.groupby("h3_cell").agg(days=("_day", "nunique"), dets=("_day", "size"))
         .sort_values(["days", "dets"], ascending=False))
    out["n_cells"] = int(len(g))
    out["cells_full"] = int((g["days"] == n).sum())
    out["cells"] = [{"h3_cell": c, "days_active": int(r.days), "days_covered": n,
                     "share": num(r.days / n, 3), "detections": int(r.dets)}
                    for c, r in g.head(limit).iterrows()]
    warnings.append("Window persistence only. Not multi-year fire memory; no persistent/emerging classes.")
    return out