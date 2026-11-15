import os
import duckdb
from fastapi import APIRouter, Query
from app.schemas.firms_nrt import FirmsResponse
from app.services.firms_ingest import DB, LABEL, LABELS

router = APIRouter(prefix="/firms", tags=["firms-nrt"])
NOTE = ("Observation counts are per-sensor detections, not unique fires. Do not compare raw counts across datasets "
        "with different windows, sensors or processing modes (NRT vs standard processing).")
UNKNOWN_LABEL = "Processing mode (NRT or standard) is not available for these rows"

FIXTURE_CELLS = [{"h3_cell": "85754e67fffffff", "lat": 15.5, "lon": 73.8, "source_dataset": "SYNTHETIC",
                  "sensor_family": "VIIRS", "platform_group": "NOAA-20", "observation_count": 3, "frp_sum": 12.0,
                  "frp_mean": 4.0, "frp_max": 7.5, "high_conf_count": 1, "acq_day": "2026-11-12",
                  "h3_res": 5, "product_type": "NRT"}]
FIXTURE_META = [{"dataset": "SYNTHETIC", "sensor": "VIIRS", "platform": "NOAA-20", "resolution": "375m",
                 "product_type": "NRT", "n_raw": 3, "n_final": 3, "exact_duplicates_dropped": 0,
                 "t_min": "2026-11-11", "t_max": "2026-11-12", "nominal_window_hours": 48.0,
                 "observed_span_hours": 24.0, "obs_per_observed_hour": 0.12, "label": LABEL}]


def _q(sql, params=()):
    if os.getenv("FIRMS_MODE", "real") == "synthetic" or not DB.exists():
        return None
    try:
        con = duckdb.connect(str(DB), read_only=True)
        try:
            return con.execute(sql, list(params)).df().to_dict("records")
        finally:
            con.close()
    except duckdb.Error:
        return None


def _label(items):
    types = {str(i.get("product_type", "")).upper() for i in items if i.get("product_type")}
    if not types:
        return UNKNOWN_LABEL
    if len(types) == 1:
        return LABELS.get(next(iter(types)), UNKNOWN_LABEL)
    return LABELS["MIXED"]


def _resp(rows, fixture):
    mode = "real" if rows is not None else "synthetic"
    items = rows if rows is not None else fixture
    return FirmsResponse(mode=mode, data_label=_label(items), note=NOTE, count=len(items), items=items)


@router.get("/datasets", response_model=FirmsResponse)
def datasets():
    return _resp(_q("SELECT * FROM firms_dataset_meta"), FIXTURE_META)


@router.get("/h3", response_model=FirmsResponse)
def h3_cells(dataset: str | None = None, limit: int = Query(5000, le=50000)):
    w, p = ("WHERE source_dataset = ?", [dataset]) if dataset else ("", [])
    return _resp(_q(f"SELECT * FROM firms_h3_cell_summary {w} ORDER BY frp_sum DESC LIMIT {int(limit)}", p), FIXTURE_CELLS)


@router.get("/heatmap/daily", response_model=FirmsResponse)
def heatmap_daily(date: str | None = None, dataset: str | None = None, limit: int = Query(20000, le=100000)):
    conds, p = [], []
    if date: conds.append("acq_day = ?"); p.append(date)
    if dataset: conds.append("source_dataset = ?"); p.append(dataset)
    w = ("WHERE " + " AND ".join(conds)) if conds else ""
    return _resp(_q(f"SELECT * FROM firms_daily_heatmap {w} ORDER BY acq_day, frp_sum DESC LIMIT {int(limit)}", p), FIXTURE_HEATMAP if False else FIXTURE_CELLS)