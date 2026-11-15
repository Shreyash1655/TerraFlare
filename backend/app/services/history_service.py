from __future__ import annotations

import pandas as pd

from app.core.config import settings


def _required_years() -> dict[str, int]:
    return {
        "season-shift": settings.season_min_years_per_period,
        "fire-memory": settings.memory_min_years,
        "anomaly": settings.anomaly_min_baseline_years,
    }


def build_history_status(obs: pd.DataFrame | None, source: str, is_synthetic: bool) -> dict:
    days, span, first, last = 0, 0, None, None
    if obs is not None and len(obs) and "acq_date" in obs.columns:
        d = pd.to_datetime(obs["acq_date"]).dt.normalize().dropna()
        if len(d):
            days = int(d.nunique())
            span = (d.max() - d.min()).days + 1
            first, last = d.min().date().isoformat(), d.max().date().isoformat()
    modules = {}
    for name, yrs in _required_years().items():
        ok = span >= yrs * 365
        modules[name] = {
            "required_years": yrs,
            "sufficient": ok,
            "message": None if ok else (
                f"Needs {yrs} years of history; have {days} observed days"
                f"{f' ({first} to {last})' if first else ''} from {source}."
            ),
        }
    return {"source": source, "is_synthetic": is_synthetic, "available_days": days,
            "span_days": span, "date_range": [first, last], "modules": modules}