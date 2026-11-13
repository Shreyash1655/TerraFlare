"""Rebuild interval_for bounds table from out-of-time Forward and Backward test errors.
Task 8b Item 6.
"""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import h3

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "terraflare.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

query = """
WITH cell_days AS (
    SELECT 
        date,
        EXTRACT(year FROM date)::INTEGER AS yr,
        EXTRACT(month FROM date)::INTEGER AS mo,
        day_night,
        h3_cell,
        SUM(CASE WHEN platform = 'S-NPP' THEN n_detections ELSE 0 END) AS snpp_cnt,
        SUM(CASE WHEN platform = 'NOAA-20' THEN n_detections ELSE 0 END) AS noaa20_cnt,
        SUM(CASE WHEN platform = 'Aqua' THEN n_detections ELSE 0 END) AS aqua_cnt,
        SUM(CASE WHEN platform = 'Terra' THEN n_detections ELSE 0 END) AS terra_cnt
    FROM cell_day_activity
    WHERE date >= '2012-01-20' AND date <= '2025-12-31'
    GROUP BY 1, 2, 3, 4, 5
)
SELECT 
    date,
    yr,
    mo,
    day_night,
    h3_cell,
    CASE 
        WHEN date >= '2022-07-27' AND date <= '2022-08-10' THEN noaa20_cnt
        ELSE snpp_cnt 
    END AS viirs_ref,
    CASE WHEN aqua_cnt > 0 THEN aqua_cnt ELSE terra_cnt END AS modis_used
FROM cell_days
"""
print("Extracting cell-day data...")
df = con.execute(query).df()
print(f"Loaded {len(df):,} cell-days.")

# Pre-compute H3 parents for spatial resolutions
print("Mapping H3 cells...")
unique_cells = df["h3_cell"].unique()
res2_map = {c: h3.cell_to_parent(c, 2) for c in unique_cells}
res3_map = {c: h3.cell_to_parent(c, 3) for c in unique_cells}
res4_map = {c: h3.cell_to_parent(c, 4) for c in unique_cells}

df["h3_res2"] = df["h3_cell"].map(res2_map)
df["h3_res3"] = df["h3_cell"].map(res3_map)
df["h3_res4"] = df["h3_cell"].map(res4_map)

# Stratum training helper
def get_strata_ratios(train_df):
    grp = train_df.groupby(["mo", "day_night"])[["viirs_ref", "modis_used"]].sum()
    r = (grp["viirs_ref"] / np.maximum(1.0, grp["modis_used"])).to_dict()
    glob = float(train_df["viirs_ref"].sum() / max(1.0, train_df["modis_used"].sum()))
    return r, glob

all_held_out_areas = []

# 1. Forward rolling origin: Y in 2016..2025
print("Running forward test predictions (2016-2025)...")
for Y in range(2016, 2026):
    tr = df[df["yr"] < Y]
    te = df[df["yr"] == Y].copy()
    r_dict, glob_r = get_strata_ratios(tr)
    strata = list(zip(te["mo"], te["day_night"]))
    te["pred"] = te["modis_used"] * np.array([r_dict.get(s, glob_r) for s in strata])
    
    # Aggregate across grains:
    # a) Country
    c_m = te.groupby(["yr", "mo"])[["pred", "viirs_ref"]].sum().reset_index()
    c_m["grain"] = "country"
    all_held_out_areas.append(c_m)
    
    # b) Res 2
    r2_m = te.groupby(["yr", "mo", "h3_res2"])[["pred", "viirs_ref"]].sum().reset_index()
    r2_m["grain"] = "res2"
    all_held_out_areas.append(r2_m[["yr", "mo", "pred", "viirs_ref", "grain"]])
    
    # c) Res 3
    r3_m = te.groupby(["yr", "mo", "h3_res3"])[["pred", "viirs_ref"]].sum().reset_index()
    r3_m["grain"] = "res3"
    all_held_out_areas.append(r3_m[["yr", "mo", "pred", "viirs_ref", "grain"]])
    
    # d) Res 4
    r4_m = te.groupby(["yr", "mo", "h3_res4"])[["pred", "viirs_ref"]].sum().reset_index()
    r4_m["grain"] = "res4"
    all_held_out_areas.append(r4_m[["yr", "mo", "pred", "viirs_ref", "grain"]])

# 2. Backward test: train on 2018-2025, test on 2012-2017
print("Running backward test predictions (2012-2017)...")
tr_bwd = df[df["yr"].isin(range(2018, 2026))]
te_bwd = df[df["yr"].isin(range(2012, 2018))].copy()
r_dict_b, glob_rb = get_strata_ratios(tr_bwd)
strata_b = list(zip(te_bwd["mo"], te_bwd["day_night"]))
te_bwd["pred"] = te_bwd["modis_used"] * np.array([r_dict_b.get(s, glob_rb) for s in strata_b])

# Country
c_mb = te_bwd.groupby(["yr", "mo"])[["pred", "viirs_ref"]].sum().reset_index()
c_mb["grain"] = "country"
all_held_out_areas.append(c_mb)

# Res 2
r2_mb = te_bwd.groupby(["yr", "mo", "h3_res2"])[["pred", "viirs_ref"]].sum().reset_index()
r2_mb["grain"] = "res2"
all_held_out_areas.append(r2_mb[["yr", "mo", "pred", "viirs_ref", "grain"]])

# Res 3
r3_mb = te_bwd.groupby(["yr", "mo", "h3_res3"])[["pred", "viirs_ref"]].sum().reset_index()
r3_mb["grain"] = "res3"
all_held_out_areas.append(r3_mb[["yr", "mo", "pred", "viirs_ref", "grain"]])

# Res 4
r4_mb = te_bwd.groupby(["yr", "mo", "h3_res4"])[["pred", "viirs_ref"]].sum().reset_index()
r4_mb["grain"] = "res4"
all_held_out_areas.append(r4_mb[["yr", "mo", "pred", "viirs_ref", "grain"]])

held_df = pd.concat(all_held_out_areas, ignore_index=True)
print(f"Total evaluated out-of-time area-months: {len(held_df):,}")

# Filter to where pred > 0 or viirs_ref > 0
held_df = held_df[(held_df["pred"] > 0) | (held_df["viirs_ref"] > 0)].copy()

# Add relative residual (yt - yhat) / yhat
held_df["rel_err"] = (held_df["viirs_ref"] - held_df["pred"]) / np.maximum(0.1, held_df["pred"])

# Size classes
size_bins = [
    ("very_small", 0, 10),
    ("small", 10, 50),
    ("medium", 50, 250),
    ("large", 250, 1000),
    ("very_large", 1000, 5000),
    ("macro", 5000, float("inf")),
]

bridge_uncertainty = 0.0184  # +/- 1.84%

print("\n=== HOLDOUT ERROR DISTRIBUTION & REBUILT INTERVALS BY SIZE CLASS ===")
bounds_table = []
for sc_name, low, high in size_bins:
    sub = held_df[(held_df["pred"] >= low) & (held_df["pred"] < high)]
    n = len(sub)
    if sc_name == "very_small" or n < 30:
        bounds_table.append({
            "size_class": sc_name,
            "range": f"[{low}, {high if high != float('inf') else 'inf'})",
            "N": n,
            "rel_lower": None,
            "rel_upper": None,
            "half_width": None,
            "reliability": "insufficient",
            "coverage_pct": 0.0,
            "rel_mae": round(float(np.mean(np.abs(sub["viirs_ref"] - sub["pred"]) / np.maximum(1.0, sub["viirs_ref"]))) * 100, 1) if n > 0 else 0.0
        })
        continue
    
    # 90% empirical quantiles: 5th and 95th percentiles of (yt - yhat)/yhat
    q5 = float(np.percentile(sub["rel_err"], 5))
    q95 = float(np.percentile(sub["rel_err"], 95))
    
    rel_l = round(max(0.0, -q5) + bridge_uncertainty, 3)
    rel_u = round(max(0.0, q95) + bridge_uncertainty, 3)
    
    # Check empirical coverage with these bounds
    y_t = sub["viirs_ref"].values
    y_p = sub["pred"].values
    lower_bound = np.maximum(0.0, y_p * (1.0 - rel_l))
    upper_bound = y_p * (1.0 + rel_u)
    covered = (y_t >= lower_bound) & (y_t <= upper_bound)
    cov_pct = round(float(np.mean(covered)) * 100, 1)
    
    # Reliability rating: if coverage is within 5 points of 90% (85% to 95%), 'medium'/'high', else 'low'
    rel_label = "medium" if cov_pct >= 85.0 else "low"
    
    rel_mae = round(float(np.mean(np.abs(y_t - y_p) / np.maximum(1.0, y_t))) * 100, 1)
    
    bounds_table.append({
        "size_class": sc_name,
        "range": f"[{low}, {high if high != float('inf') else 'inf'})",
        "N": n,
        "rel_lower": rel_l,
        "rel_upper": rel_u,
        "half_width": round((rel_l + rel_u) / 2.0, 3),
        "reliability": rel_label,
        "coverage_pct": cov_pct,
        "rel_mae": rel_mae,
    })

bt_df = pd.DataFrame(bounds_table)
print(bt_df.to_string())

# Check country-level coverage specifically:
country_sub = held_df[held_df["grain"] == "country"]
print(f"\nCountry-Level Area-Months Evaluated: {len(country_sub)}")
v_c = country_sub["viirs_ref"].values
p_c = country_sub["pred"].values
# Look at macro bounds on country level
macro_row = [r for r in bounds_table if r["size_class"] == "macro"][0]
if macro_row["rel_lower"] is not None:
    l_c = np.maximum(0.0, p_c * (1.0 - macro_row["rel_lower"]))
    u_c = p_c * (1.0 + macro_row["rel_upper"])
    c_cov = float(np.mean((v_c >= l_c) & (v_c <= u_c))) * 100
    print(f"Empirical Country-Level Coverage under macro bounds: {c_cov:.1f}%")

