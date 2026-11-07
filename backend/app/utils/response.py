from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from app.core.config import settings


def num(x: Any, nd: int = 4) -> float | None:
    """NaN/None -> None, otherwise a rounded Python float (JSON safe)."""
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(x), nd)


def iso(d: Any) -> str | None:
    if d is None or (not isinstance(d, (list, dict)) and pd.isna(d)):
        return None
    return pd.Timestamp(d).date().isoformat()


def to_records(df: pd.DataFrame) -> list[dict]:
    out = df.astype(object).where(df.notna(), None).to_dict("records")
    for r in out:
        for k, v in r.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                r[k] = v.isoformat()
    return out


def make_envelope(repo, data: dict, parameters: dict | None = None, limitations: list[str] | None = None) -> dict:
    params = {
        k: (v.isoformat() if isinstance(v, (date, datetime)) else v)
        for k, v in (parameters or {}).items()
        if v is not None
    }
    return {
        "meta": {
            "api_version": settings.api_version,
            "data_version": repo.data_version,
            "data_mode": repo.mode,
            "is_synthetic": repo.is_synthetic,
            "method_id": repo.method_id,
            "generated_at": datetime.now(timezone.utc),
            "parameters": params,
            "limitations": limitations or [],
        },
        "data": data,
    }   