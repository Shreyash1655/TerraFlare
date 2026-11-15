import pandas as pd
from pathlib import Path

LOG = Path(r"C:\Users\shrey\TerraFlare\backend\app\data\processed\firms\ingest_log.parquet")
OBS = Path(r"C:\Users\shrey\TerraFlare\data\staging_obs_clean.parquet")
OUT = LOG.with_name("coverage_day.parquet")

log = pd.read_parquet(LOG)
u = log["source_id"].str.upper()
log["sensor"] = pd.Series(pd.NA, index=log.index, dtype="object")
log.loc[u.str.startswith("MODIS"), "sensor"] = "MODIS"
log.loc[u.str.startswith("J1_VIIRS"), "sensor"] = "VIIRS"   # NOAA-20 only; J2 excluded
log = log.dropna(subset=["sensor"])
log["d0"] = pd.to_datetime(log["t_min"]).dt.normalize()
log["d1"] = pd.to_datetime(log["t_max"]).dt.normalize()

obs = pd.read_parquet(OBS, columns=["sensor_family", "platform", "local_date"])
obs = obs[(obs.sensor_family == "MODIS") | ((obs.sensor_family == "VIIRS") & (obs.platform == "NOAA-20"))]
obs["local_date"] = pd.to_datetime(obs["local_date"]).dt.normalize()
counts = obs.groupby(["local_date", "sensor_family"]).size().unstack(fill_value=0)

days = pd.date_range(min(log.d0.min(), counts.index.min()), max(log.d1.max(), counts.index.max()), freq="D")
res = pd.DataFrame(index=days)
for s in ("VIIRS", "MODIS"):
    segs = []
    for a, b in sorted(zip(log.loc[log.sensor == s, "d0"], log.loc[log.sensor == s, "d1"])):
        if segs and a <= segs[-1][1] + pd.Timedelta(days=1):
            segs[-1][1] = max(segs[-1][1], b)
        else:
            segs.append([a, b])
    in_range = pd.Series(False, index=days)
    for a, b in segs:   # local day D complete if UTC days D-1..D are inside the segment
        in_range[(days >= a + pd.Timedelta(days=1)) & (days <= b)] = True
    n = counts[s].reindex(days).fillna(0).astype(int) if s in counts else pd.Series(0, index=days)
    res[f"{s.lower()}_n"] = n
    res[f"{s.lower()}_in_range"] = in_range
    res[f"{s.lower()}_suspect_zero"] = in_range & (n == 0)
    res[f"{s.lower()}_covered"] = in_range & (n > 0)
res.index.name = "acq_date"
res.reset_index().to_parquet(OUT, index=False)
print("wrote", OUT, len(res), "days")
y = res.index.year
print(res[["viirs_covered", "modis_covered", "viirs_suspect_zero", "modis_suspect_zero"]].groupby(y).sum().to_string())
print("both covered:", int((res.viirs_covered & res.modis_covered).sum()))