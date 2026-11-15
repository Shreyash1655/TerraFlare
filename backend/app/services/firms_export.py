"""Export FIRMS observations (NRT and standard processing) in the obs_clean / ingest_log schema used by DataRepository.
CLI: python -m app.services.firms_export <raw_dir>   (run after firms_ingest process)
Footprint rule: NRT rows are kept only in H3 cells that contain at least one standard-processing (SP) detection,
so a country-clipped SP series and a global NRT series cover the same area."""
import sys, hashlib
import pandas as pd
from app.services.firms_ingest import PROC, LABEL, find_shps

CONF = {"low": "low", "nominal": "medium", "high": "high"}  # fixture vocabulary: medium/high


def export(raw_dir: str):
    d = PROC / "firms"
    o = pd.read_parquet(d / "observations.parquet")
    meta = pd.read_parquet(d / "dataset_meta.parquet")
    n_before = o.groupby("source_dataset").size()
    sp_cells = set(o.loc[o["product_type"] == "SP", "h3_cell"].unique())
    if sp_cells:
        o = o[(o["product_type"] == "SP") | o["h3_cell"].isin(sp_cells)].copy()
        n_after = o.groupby("source_dataset").size().reindex(n_before.index).fillna(0).astype(int)
        print("footprint cells (from SP):", len(sp_cells))
        print(pd.DataFrame({"before": n_before, "after": n_after, "dropped": n_before - n_after}).to_string())
    else:
        n_after = n_before
        print("WARNING: no SP rows, footprint filter not applied")
    ts = o["acq_datetime_utc"].dt.tz_convert("UTC").dt.tz_localize(None)  # naive UTC, like the fixture
    out = pd.DataFrame({
        "acq_date": ts.dt.normalize(), "acq_datetime_utc": ts, "region_id": "global",
        "lat": o["latitude"], "lon": o["longitude"], "sensor_family": o["sensor_family"], "platform": o["platform"],
        "frp_mw": o["frp"], "is_valid": True, "confidence_raw": o["confidence_native"],
        "confidence_class": o["confidence_class"].map(CONF).fillna("unknown"),
        "source_dataset": o["source_dataset"], "record_id": o["record_id"], "product_type": o["product_type"],
        "h3_cell": o["h3_cell"], "daynight": o["daynight"], "satellite": o["satellite"], "product_version": o["version"],
        "brightness_primary": o["brightness_primary"], "brightness_secondary": o["brightness_secondary"],
        "scan": o["scan"], "track": o["track"],
    })
    out.to_parquet(d / "obs_clean.parquet", index=False)
    hashes = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in find_shps(raw_dir)}
    ver = o.groupby("source_dataset")["version"].first()
    log = pd.DataFrame({
        "source_id": meta["dataset"], "product_version": meta["dataset"].map(ver), "file_name": meta["dataset"] + ".shp",
        "sha256": meta["dataset"].map(hashes), "rows_in": meta["n_raw"],
        "rows_out": meta["dataset"].map(n_after).fillna(0).astype(int),
        "ingested_at": pd.Timestamp.now("UTC").tz_localize(None), "product_type": meta["product_type"],
        "data_label": meta["label"],
        "t_min": meta["t_min"], "t_max": meta["t_max"], "nominal_window_hours": meta["nominal_window_hours"],
        "observed_span_hours": meta["observed_span_hours"],
    })
    log.to_parquet(d / "ingest_log.parquet", index=False)
    print(len(out), "obs_clean rows;", len(log), "ingest_log rows ->", d)


if __name__ == "__main__":
    export(sys.argv[1])