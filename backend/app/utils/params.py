from __future__ import annotations

import pandas as pd

from app.core.config import settings
from app.utils.errors import TerraFlareError


def resolve_range(repo, start=None, end=None, default_days: int = 365, max_days: int | None = None):
    """Validate start/end, default to the latest `default_days` of data, clip to the dataset."""
    if start and end and pd.Timestamp(start) > pd.Timestamp(end):
        raise TerraFlareError("invalid_date_range", "start must be before end", 400)
    dmin, dmax = repo.data_range()
    e = min(pd.Timestamp(end), dmax) if end else dmax
    s = max(pd.Timestamp(start), dmin) if start else max(dmin, e - pd.Timedelta(days=default_days - 1))
    if s > e:
        raise TerraFlareError("no_data_in_range", "No data in the requested range", 404,
                              {"dataset_start": dmin.date().isoformat(), "dataset_end": dmax.date().isoformat()})
    limit = max_days or settings.max_range_days
    if (e - s).days + 1 > limit:
        raise TerraFlareError("range_too_large", f"Range is limited to {limit} days", 400)
    return s, e