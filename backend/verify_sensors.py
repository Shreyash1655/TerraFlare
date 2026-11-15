"""TerraFlare data verification: sensor IDs, dates, spatial overlap, alignment.

Run from the backend folder (venv active):
    python verify_sensors.py                      # checks the FIRMS obs_clean + harmonized mart
    python verify_sensors.py OBS.parquet MART.parquet
Read-only. Prints PASS / WARN / FAIL per check. Never modifies data.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

OBS = sys.argv[1] if len(sys.argv) > 1 else "app/data/processed/firms/obs_clean.parquet"
MART = sys.argv[2] if len(sys.argv) > 2 else "../data/marts/harmonized_cell_day.parquet"

EXPECTED = {
    "MODIS": {"Terra", "Aqua"},
    "VIIRS": {"S-NPP", "NOAA-20", "NOAA-21"},
}
# India data region used by the API (api_envelope.py)
MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 68.0, 6.5, 97.5, 37.5

results: list[tuple[str, str, str]] = []


def report(level: str, name: str, detail: str = "") -> None:
    results.append((level, name, detail))
    print(f"[{level}] {name}" + (f" -> {detail}" if detail else ""))


def q(con, sql, *a):
    return con.execute(sql, list(a)).fetchall()


def main() -> int:
    for p in (OBS, MART):
        if not Path(p).exists():
            report("FAIL", "file exists", p)
            return 1
    con = duckdb.connect()
    con.execute(f"CREATE VIEW obs AS SELECT * FROM read_parquet('{OBS}')")
    con.execute(f"CREATE VIEW mart AS SELECT * FROM read_parquet('{MART}')")
    cols = {r[0] for r in q(con, "DESCRIBE obs")}
    total = q(con, "SELECT COUNT(*) FROM obs")[0][0]
    print(f"\nobs_clean: {OBS}\nrows: {total:,}\ncolumns: {sorted(cols)}\n")

    need = {"sensor_family", "platform", "acq_date", "lat", "lon"}
    missing = need - cols
    if missing:
        report("FAIL", "required columns", f"missing {sorted(missing)}")
        return 1
    report("PASS", "required columns present")

    # 1. Provenance flags -------------------------------------------------
    if "is_synthetic" in cols:
        n = q(con, "SELECT COUNT(*) FILTER (WHERE is_synthetic) FROM obs")[0][0]
        report("FAIL" if n else "PASS", "is_synthetic rows", f"{n:,} of {total:,}")
    else:
        report("WARN", "is_synthetic column absent", "cannot prove data is real")
    for c in ("processing_stream", "product_version", "source_id"):
        if c in cols:
            print(c, q(con, f"SELECT {c}, COUNT(*) FROM obs GROUP BY 1 ORDER BY 2 DESC LIMIT 10"))

    # 2. Sensor / platform identifiers ------------------------------------
    rows = q(con, "SELECT sensor_family, platform, COUNT(*) FROM obs GROUP BY 1,2 ORDER BY 1,2")
    print("\nsensor_family x platform:")
    for r in rows:
        print("  ", r)
    bad = [(s, p, n) for s, p, n in rows if s not in EXPECTED or p not in EXPECTED.get(s, set())]
    nulls = q(con, "SELECT COUNT(*) FROM obs WHERE sensor_family IS NULL OR platform IS NULL")[0][0]
    if bad or nulls:
        report("FAIL", "sensor/platform identifiers", f"unexpected={bad} nulls={nulls}")
    else:
        report("PASS", "sensor/platform identifiers match expected set")
    present = {s: {p for s2, p, _ in rows if s2 == s} for s in EXPECTED}
    for s, exp in EXPECTED.items():
        if not present.get(s):
            report("FAIL", f"{s} has no observations")
        elif exp - present[s]:
            report("WARN", f"{s} platforms absent", str(sorted(exp - present[s])))
    if "satellite_raw" in cols:
        print("raw satellite -> platform:", q(con, "SELECT satellite_raw, platform, COUNT(*) FROM obs GROUP BY 1,2 ORDER BY 3 DESC LIMIT 15"))

    # 3. Acquisition dates ------------------------------------------------
    d0, d1, dn = q(con, "SELECT MIN(acq_date), MAX(acq_date), COUNT(*) FILTER (WHERE acq_date IS NULL) FROM obs")[0]
    print(f"\nacq_date range: {d0} -> {d1}  (null: {dn})")
    report("FAIL" if dn else "PASS", "acq_date nulls", str(dn))
    fut = q(con, "SELECT COUNT(*) FROM obs WHERE acq_date > CURRENT_DATE")[0][0]
    report("FAIL" if fut else "PASS", "future acquisition dates", str(fut))
    if "acq_datetime_utc" in cols:
        mis = q(con, "SELECT COUNT(*) FROM obs WHERE acq_datetime_utc IS NOT NULL AND CAST(acq_datetime_utc AS DATE) <> CAST(acq_date AS DATE)")[0][0]
        report("WARN" if mis else "PASS", "acq_date vs acq_datetime_utc (UTC date)", f"{mis:,} differ")
    print("per sensor/platform date range:")
    for r in q(con, "SELECT sensor_family, platform, MIN(acq_date), MAX(acq_date), COUNT(DISTINCT acq_date) FROM obs GROUP BY 1,2 ORDER BY 1,2"):
        print("  ", r)

    # 4. Spatial validity -------------------------------------------------
    inv = q(con, "SELECT COUNT(*) FROM obs WHERE lat IS NULL OR lon IS NULL OR lat NOT BETWEEN -90 AND 90 OR lon NOT BETWEEN -180 AND 180")[0][0]
    report("FAIL" if inv else "PASS", "invalid lat/lon", str(inv))
    out = q(con, f"SELECT sensor_family, COUNT(*) FROM obs WHERE lat NOT BETWEEN {MIN_LAT} AND {MAX_LAT} OR lon NOT BETWEEN {MIN_LON} AND {MAX_LON} GROUP BY 1")
    report("WARN" if out else "PASS", "points outside India data region", str(out))
    if "h3_cell" in cols:
        nh = q(con, "SELECT COUNT(*) FROM obs WHERE h3_cell IS NULL")[0][0]
        report("WARN" if nh else "PASS", "null h3_cell", f"{nh:,}")
    try:  # region bounding boxes from the app config
        from app.shared.regions import load_regions
        print("\nregion bbox counts (valid rows):")
        for rid, reg in load_regions().items():
            b = reg.bbox
            r = q(con, "SELECT sensor_family, COUNT(*) FROM obs WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? "
                       + ("AND is_valid " if "is_valid" in cols else "") + "GROUP BY 1",
                  b.min_lat, b.max_lat, b.min_lon, b.max_lon)
            d = dict(r)
            print(f"   {rid:20s} MODIS={d.get('MODIS', 0):,} VIIRS={d.get('VIIRS', 0):,}")
            if not d:
                report("WARN", f"region '{rid}' has no observations")
    except Exception as e:  # noqa: BLE001
        report("WARN", "region bbox check skipped", str(e))
    print("\nmart region_id coverage:",
          q(con, "SELECT region_id, COUNT(*), COUNT(DISTINCT acq_date) FROM mart GROUP BY 1 ORDER BY 2 DESC"))

    # 5. Temporal alignment / overlap (observations) ----------------------
    both = q(con, "SELECT COUNT(*) FROM (SELECT acq_date FROM obs GROUP BY 1 HAVING COUNT(*) FILTER (WHERE sensor_family='MODIS')>0 AND COUNT(*) FILTER (WHERE sensor_family='VIIRS')>0)")[0][0]
    days = q(con, "SELECT COUNT(DISTINCT acq_date) FROM obs")[0][0]
    report("PASS" if both >= 14 else "WARN", "days with both MODIS and VIIRS", f"{both} of {days}")
    if "h3_cell" in cols:
        sp = q(con, "SELECT COUNT(*) FROM (SELECT h3_cell FROM obs WHERE h3_cell IS NOT NULL GROUP BY 1 HAVING COUNT(DISTINCT sensor_family)=2)")[0][0]
        cells = q(con, "SELECT COUNT(DISTINCT h3_cell) FROM obs")[0][0]
        report("PASS" if sp else "WARN", "H3 cells seen by both sensors (spatial overlap)", f"{sp:,} of {cells:,}")

    # 6. Observations vs harmonized mart ----------------------------------
    mc = {r[0] for r in q(con, "DESCRIBE mart")}
    print(f"\nmart columns: {sorted(mc)}")
    m0, m1, mr = q(con, "SELECT MIN(acq_date), MAX(acq_date), COUNT(*) FROM mart")[0]
    print(f"mart: {mr:,} rows, {m0} -> {m1}")
    lo, hi = (q(con, "SELECT MIN(local_date), MAX(local_date) FROM obs")[0]
              if "local_date" in cols else (d0, d1))
    if lo and m0 and (m0 < lo or m1 > hi):
        report("FAIL", "mart dates outside observation local_date range",
               f"mart {m0}->{m1} vs obs local_date {lo}->{hi}")
    else:
        report("PASS", "mart dates within observation local_date range",
               f"mart {m0}->{m1} (mart uses local solar date), obs local_date {lo}->{hi}")
    if "h3_cell" in cols and "h3_cell" in mc:
        orphan = q(con, "SELECT COUNT(DISTINCT h3_cell) FROM mart WHERE h3_cell NOT IN (SELECT DISTINCT h3_cell FROM obs WHERE h3_cell IS NOT NULL)")[0][0]
        report("FAIL" if orphan else "PASS", "mart cells absent from observations", f"{orphan:,}")
    mod_obs = q(con, "SELECT COUNT(*) FROM obs WHERE sensor_family='MODIS'" + (" AND is_valid" if "is_valid" in cols else ""))[0][0]
    vii_obs = q(con, "SELECT COUNT(*) FROM obs WHERE sensor_family='VIIRS'" + (" AND is_valid" if "is_valid" in cols else ""))[0][0]
    ms = q(con, "SELECT COALESCE(SUM(modis_observed),0), COALESCE(SUM(viirs_observed),0) FROM mart")[0]
    print(f"valid obs MODIS/VIIRS: {mod_obs:,}/{vii_obs:,}  vs mart sums: {ms[0]:,.0f}/{ms[1]:,.0f}")
    vp = [x[0] for x in q(con, "SELECT DISTINCT viirs_platform FROM mart WHERE viirs_platform IS NOT NULL")]
    print("mart viirs_platform:", vp)
    ref = q(con, "SELECT COUNT(*) FROM obs WHERE sensor_family='VIIRS' AND platform IN "
                 "(SELECT DISTINCT viirs_platform FROM mart)"
                 + (" AND is_valid" if "is_valid" in cols else ""))[0][0]
    for name, a, b in (("MODIS", mod_obs, ms[0]), ("VIIRS reference platform", ref, ms[1])):
        ratio = (b / a) if a else None
        report("WARN" if ratio is None or abs(ratio - 1) > 0.05 else "PASS",
               f"mart {name} total vs valid observations", f"ratio={ratio}")

    print("\n==== SUMMARY ====")
    for lvl in ("FAIL", "WARN", "PASS"):
        print(lvl, sum(1 for r in results if r[0] == lvl))
    return 1 if any(r[0] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())