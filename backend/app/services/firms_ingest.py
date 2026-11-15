"""FIRMS shapefile ingestion (NRT and standard processing). CLI: python -m app.services.firms_ingest validate|process <raw_dir>
Footprint rule: NRT rows are kept only in H3 cells that contain at least one standard-processing (SP) detection."""
import os, sys, json
from pathlib import Path
import numpy as np, pandas as pd, duckdb, h3
from pyogrio.raw import read as ogr_read

REQ = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
PROC = Path(os.getenv("FIRMS_PROCESSED_DIR", "app/data/processed"))
DB = Path(os.getenv("FIRMS_DB", str(PROC / "firms.duckdb")))
H3_RES = int(os.getenv("FIRMS_H3_RES", "5"))
LABELS = {"NRT": "NRT (near real-time) data - not standard science-quality historical data",
          "SP": "Standard processing (science-quality) data",
          "MIXED": "Mixed NRT and standard-processing data"}
LABEL = LABELS["NRT"]  # kept for backward-compatible imports
PLATFORM = {"T": "Terra", "A": "Aqua", "N": "Suomi-NPP", "N20": "NOAA-20", "N21": "NOAA-21"}


def dataset_meta(name: str) -> dict:
    n = name.upper()
    if n.startswith("MODIS"):
        return {"sensor": "MODIS", "platform": "Terra+Aqua", "resolution": "1 km"}
    if n.startswith("J1_VIIRS"):
        return {"sensor": "VIIRS", "platform": "NOAA-20", "resolution": "375 m"}
    if n.startswith("J2_VIIRS"):
        return {"sensor": "VIIRS", "platform": "NOAA-21", "resolution": "375 m"}
    return {"sensor": "UNKNOWN", "platform": "UNKNOWN", "resolution": "?"}


def check_components(shp: Path) -> list:
    return [e for e in REQ if not shp.with_suffix(e).exists()]


def load(shp: Path) -> pd.DataFrame:
    meta, _, _, data = ogr_read(str(shp), read_geometry=False)  # honors .cpg encoding
    return pd.DataFrame({f.lower(): d for f, d in zip(meta["fields"], data)})


def normalize(shp: Path):
    """Return (clean_df, stats). Native columns preserved; unified columns added."""
    name = shp.stem
    raw = load(shp)
    df = raw.copy()
    m = dataset_meta(name)
    df["source_dataset"] = name
    df["source_file"] = shp.name
    df["sensor_family"] = m["sensor"]
    df["platform_group"] = m["platform"]
    df["platform"] = df["satellite"].astype(str).str.strip().map(PLATFORM).fillna(df["satellite"].astype(str))
    # NRT versions contain "NRT" (e.g. 6.1NRT, 2.0NRT); standard processing does not (6.1, 2.0)
    df["product_type"] = np.where(df["version"].astype(str).str.upper().str.contains("NRT"), "NRT", "SP")
    b1 = "brightness" if "brightness" in df else "bright_ti4"
    b2 = "bright_t31" if "bright_t31" in df else "bright_ti5"
    df["brightness_primary"] = pd.to_numeric(df[b1], errors="coerce")
    df["brightness_secondary"] = pd.to_numeric(df[b2], errors="coerce")
    # acquisition time is HHMM in UTC
    t = df["acq_time"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4).str[-4:]
    hh = pd.to_numeric(t.str[:2], errors="coerce"); mm = pd.to_numeric(t.str[2:], errors="coerce")
    d = pd.to_datetime(df["acq_date"].astype(str).str[:10], errors="coerce")
    ok_hm = hh.between(0, 23) & mm.between(0, 59)
    df["acq_datetime_utc"] = (d + pd.to_timedelta(hh, unit="h") + pd.to_timedelta(mm, unit="m")).where(ok_hm)
    df["acq_day"] = df["acq_datetime_utc"].dt.strftime("%Y-%m-%d")
    # native confidence preserved as-is; class is a separate derived column
    df["confidence_native"] = df["confidence"].astype(str).str.strip()
    if m["sensor"] == "MODIS":
        c = pd.to_numeric(df["confidence"], errors="coerce")
        df["confidence_class"] = pd.cut(c, [-1, 29.999, 79.999, 100], labels=["low", "nominal", "high"]).astype(str)
    else:
        df["confidence_class"] = df["confidence_native"].str.lower().map(
            {"l": "low", "low": "low", "n": "nominal", "nominal": "nominal", "h": "high", "high": "high"}).fillna("unknown")
    df["is_high_conf"] = (df["confidence_class"] == "high").astype(int)
    lat = pd.to_numeric(df["latitude"], errors="coerce"); lon = pd.to_numeric(df["longitude"], errors="coerce")
    frp = pd.to_numeric(df["frp"], errors="coerce")
    ok_coord = lat.between(-90, 90) & lon.between(-180, 180)
    ok_frp = frp.notna() & (frp >= 0)
    ok_time = df["acq_datetime_utc"].notna()
    df["latitude"], df["longitude"], df["frp"] = lat, lon, frp
    valid = ok_coord & ok_frp & ok_time
    # source-record identity = exact match on every native observation attribute
    key = (df["source_dataset"] + "|" + df["latitude"].round(5).astype(str) + "|" + df["longitude"].round(5).astype(str)
           + "|" + df["acq_datetime_utc"].astype(str) + "|" + df["satellite"].astype(str)
           + "|" + df["scan"].astype(str) + "|" + df["track"].astype(str)
           + "|" + df["frp"].astype(str) + "|" + df["confidence_native"] + "|" + df[b1].astype(str))
    df["record_id"] = pd.util.hash_pandas_object(key, index=False).astype("uint64").map(lambda x: f"{x:016x}")
    clean = df[valid]
    n_valid = len(clean)
    clean = clean.drop_duplicates("record_id")
    stats = {
        "dataset": name, **m, "columns": list(raw.columns), "n_raw": len(raw), "n_valid": n_valid,
        "bad_coord": int((~ok_coord).sum()), "bad_frp": int((~ok_frp).sum()), "bad_time": int((~ok_time).sum()),
        "exact_duplicates_dropped": n_valid - len(clean), "n_final": len(clean),
        "t_min": str(clean.acq_datetime_utc.min()), "t_max": str(clean.acq_datetime_utc.max()),
        "frp_min": float(clean.frp.min()), "frp_max": float(clean.frp.max()),
        "confidence_class": clean.confidence_class.value_counts().to_dict(),
        "satellite": clean["satellite"].astype(str).value_counts().to_dict(),
        "version": clean["version"].astype(str).value_counts().to_dict(),
        "product_type": clean["product_type"].value_counts().to_dict(),
        "daynight": clean["daynight"].astype(str).value_counts().to_dict(),
        "per_day": clean.acq_day.value_counts().sort_index().to_dict(),
    }
    return clean, stats


def find_shps(raw_dir: str):
    return sorted(Path(raw_dir).rglob("*.shp"))


def validate(raw_dir: str):
    for shp in find_shps(raw_dir):
        miss = check_components(shp)
        print(f"\n=== {shp.stem} | missing components: {miss or 'none'}")
        if ".shp" in miss or ".dbf" in miss:
            continue
        _, s = normalize(shp)
        print(json.dumps(s, indent=1, default=str))


def process(raw_dir: str):
    frames, metas = [], []
    for shp in find_shps(raw_dir):
        if check_components(shp):
            print("SKIP (incomplete):", shp.stem, check_components(shp)); continue
        df, s = normalize(shp)
        span = max((df.acq_datetime_utc.max() - df.acq_datetime_utc.min()).total_seconds() / 3600, 1)
        nominal = 168 if "7d" in shp.stem.lower() else 48 if "48h" in shp.stem.lower() else span
        pt = df["product_type"].unique()
        ptype = pt[0] if len(pt) == 1 else "MIXED"
        metas.append({"dataset": s["dataset"], "sensor": s["sensor"], "platform": s["platform"],
                      "resolution": s["resolution"], "product_type": ptype, "n_raw": s["n_raw"], "n_final": s["n_final"],
                      "n_before_footprint": s["n_final"],
                      "exact_duplicates_dropped": s["exact_duplicates_dropped"], "t_min": s["t_min"], "t_max": s["t_max"],
                      "nominal_window_hours": float(nominal), "observed_span_hours": round(span, 1),
                      "obs_per_observed_hour": round(s["n_final"] / span, 2),
                      "label": LABELS[ptype]})
        frames.append(df)
    obs = pd.concat(frames, ignore_index=True)
    # MODIS confidence is numeric 0-100, VIIRS is l/n/h text: keep native value as text, numeric form separately
    obs["confidence_numeric"] = pd.to_numeric(obs["confidence"], errors="coerce")
    obs["confidence"] = obs["confidence"].astype(str)
    ll = obs[["latitude", "longitude"]].drop_duplicates().copy()
    ll["h3_cell"] = [h3.latlng_to_cell(a, b, H3_RES) for a, b in zip(ll.latitude, ll.longitude)]
    obs = obs.merge(ll, on=["latitude", "longitude"], how="left")
    obs["acq_datetime_utc"] = obs["acq_datetime_utc"].dt.tz_localize("UTC")

    # Footprint rule: NRT rows only in H3 cells containing >=1 SP detection (same area for both streams).
    sp_cells = set(obs.loc[obs["product_type"] == "SP", "h3_cell"].unique())
    if sp_cells:
        n_before = obs.groupby("source_dataset").size()
        obs = obs[(obs["product_type"] == "SP") | obs["h3_cell"].isin(sp_cells)].copy()
        n_after = obs.groupby("source_dataset").size().reindex(n_before.index).fillna(0).astype(int)
        for m in metas:
            m["n_final"] = int(n_after.get(m["dataset"], 0))
        print("footprint cells (from SP):", len(sp_cells))
        print(pd.DataFrame({"before": n_before, "after": n_after, "dropped": n_before - n_after}).to_string())
    else:
        print("WARNING: no SP rows, footprint filter not applied")

    def agg(g):
        return g.agg(observation_count=("record_id", "size"), frp_sum=("frp", "sum"), frp_mean=("frp", "mean"),
                     frp_max=("frp", "max"), high_conf_count=("is_high_conf", "sum")).reset_index()
    keys = ["source_dataset", "sensor_family", "platform_group", "product_type"]
    cells = agg(obs.groupby(keys + ["h3_cell"]))
    daily = agg(obs.groupby(keys + ["acq_day", "h3_cell"]))
    for t in (cells, daily):
        c = {x: h3.cell_to_latlng(x) for x in t.h3_cell.unique()}
        t["lat"] = t.h3_cell.map(lambda x: c[x][0]); t["lon"] = t.h3_cell.map(lambda x: c[x][1])
        t["h3_res"] = H3_RES
    (PROC / "firms").mkdir(parents=True, exist_ok=True)
    meta = pd.DataFrame(metas)
    tables = {"observations": ("firms_observations", obs), "h3_cell_summary": ("firms_h3_cell_summary", cells),
              "daily_heatmap": ("firms_daily_heatmap", daily), "dataset_meta": ("firms_dataset_meta", meta)}
    con = duckdb.connect(str(DB))
    for fn, (tbl, df) in tables.items():
        df.to_parquet(PROC / "firms" / f"{fn}.parquet", index=False)
        con.register("_t", df); con.execute(f"CREATE OR REPLACE TABLE {tbl} AS SELECT * FROM _t"); con.unregister("_t")
    con.close()
    print(meta.to_string()); print("obs:", len(obs), "cells:", len(cells), "daily rows:", len(daily), "->", DB)


if __name__ == "__main__":
    {"validate": validate, "process": process}[sys.argv[1]](sys.argv[2])