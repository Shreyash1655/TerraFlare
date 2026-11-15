import shutil, pandas as pd
from pathlib import Path
from app.core.harmonization import calibration as cal
from app.core.harmonization.temporal import aggregate_cell_day_activity

src = Path(r"C:\Users\shrey\TerraFlare\data\staging_obs_clean.parquet")
out = Path(r"C:\Users\shrey\TerraFlare\data_hackathon")
if out.exists():
    shutil.copytree(out, out.with_name("data_hackathon_bak_prev"), dirs_exist_ok=True)
out.mkdir(exist_ok=True)
db = Path(r"C:\Users\shrey\TerraFlare\data\terraflare.duckdb")
shutil.copy(db, db.with_suffix(".duckdb.bak"))

obs = pd.read_parquet(src)
print("streams:", obs["processing_stream"].value_counts().to_dict())

# Calibration is fitted on standard-processing (SP) data ONLY; NRT is excluded by prepare_calibration_data.
fit = cal.prepare_calibration_data(obs)
assert set(fit["processing_stream"].astype(str).str.upper().unique()) == {"SP"}, "non-SP rows in calibration data"
print("calibration rows:", len(fit), fit["platform"].value_counts().to_dict(),
      fit["acq_date"].min(), fit["acq_date"].max())

cd = aggregate_cell_day_activity(obs)  # mart uses SP + NRT, NRT flagged is_provisional
print("cell-day rows:", cd.shape)
print(cd.groupby("platform")["date"].agg(["min", "max", "count"]))

suite = cal.fit_calibration_suite(obs)
print("grain:", suite.training_grain, "| held-out monthly MAE day/week:", suite.mae_monthly_day, suite.mae_monthly_week)
print("bridge:", suite.bridge_info)
for m in (suite.terra_model, suite.aqua_model):
    print(m.platform, "method", m.method_id, "ratio", m.global_ratio, "n strata", len(m.strata_ratios))
    print("  metrics (in-sample)", m.metrics)
    print("  uncertainty", m.uncertainty)

h = cal.apply_calibration_to_cell_days(cd, suite, data_dir=out, data_version="sp2021-2025+nrt2026-india")
print(h.shape)
print(h["value_type"].value_counts())
print(h["is_provisional"].value_counts())
print(h.groupby("viirs_platform")["harmonized_value"].sum())