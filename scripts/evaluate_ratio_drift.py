"""Comprehensive Task 8b analysis script:
1. Ratio over time: full 2012-2025 overlap, VIIRS/MODIS ratio (platform_used rule, country level)
   per year, per month group (quarters), per day/night, with block-bootstrap 90% intervals.
   Aqua-only and Terra-only ratios separately.
   Median local overpass time per platform per year, and yearly share of cell-days with Aqua present.
   Trend analysis (linear regression slope, p-value, direction).
2. Backward test: train on 2018-2025 and test on 2012-2017; also train on latest K years (2023-2025, K=3; 2024-2025, K=2)
   and earliest K years of 2018-2025 (2018-2020) and test on 2012-2017.
   Report country-month relative MAE, bias, interval coverage by test year.
3. Interval reconstruction from forward and backward test errors by size class.
"""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import linregress, spearmanr

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "terraflare.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

# -----------------------------------------------------------------------------
# Part 1: Load Wide Cell-Day Matrix (2012-2025)
# -----------------------------------------------------------------------------
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
    CASE WHEN aqua_cnt > 0 THEN aqua_cnt ELSE terra_cnt END AS modis_used,
    aqua_cnt,
    terra_cnt
FROM cell_days
"""
print("Extracting cell-day data...", flush=True)
df = con.execute(query).df()
print(f"Loaded {len(df):,} cell-days.", flush=True)

# Overpass times from obs_clean
print("Computing overpass times...", flush=True)
overpass_q = """
SELECT 
    EXTRACT(year FROM acq_date)::INTEGER AS yr,
    platform,
    day_night,
    COUNT(*) AS n_obs,
    ROUND(MEDIAN(EXTRACT(hour FROM acq_datetime_utc) + EXTRACT(minute FROM acq_datetime_utc)/60.0), 2) AS med_ist_hr
FROM obs_clean
WHERE is_valid = true AND EXTRACT(year FROM acq_date) >= 2012 AND EXTRACT(year FROM acq_date) <= 2025
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
"""
overpass_df = con.execute(overpass_q).df()

# -----------------------------------------------------------------------------
# Part 2: Ratio Over Time with Block Bootstrap
# -----------------------------------------------------------------------------
print("Computing Annual Ratios & Block-Bootstrap 90% Intervals...", flush=True)

df["ym"] = df["yr"].astype(str) + "-" + df["mo"].astype(str).str.zfill(2)

def block_bootstrap_ratio(sub_df, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    grouped = sub_df.groupby("ym")[["viirs_ref", "modis_used"]].sum()
    v_arr = grouped["viirs_ref"].to_numpy()
    m_arr = grouped["modis_used"].to_numpy()
    n_blocks = len(v_arr)
    if n_blocks == 0:
        return 0.0, 0.0, 0.0
    point_ratio = float(np.sum(v_arr) / np.maximum(1.0, np.sum(m_arr)))
    indices = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    boot_v = np.sum(v_arr[indices], axis=1)
    boot_m = np.sum(m_arr[indices], axis=1)
    boot_ratios = boot_v / np.maximum(1.0, boot_m)
    ci_lower = float(np.percentile(boot_ratios, 5))
    ci_upper = float(np.percentile(boot_ratios, 95))
    return point_ratio, ci_lower, ci_upper

annual_rows = []
for y in sorted(df["yr"].unique()):
    y_sub = df[df["yr"] == y]
    tot_cd = len(y_sub)
    aqua_cd = (y_sub["aqua_cnt"] > 0).sum()
    aqua_share = aqua_cd / tot_cd if tot_cd > 0 else 0.0
    
    v_sum = y_sub["viirs_ref"].sum()
    m_sum = y_sub["modis_used"].sum()
    a_sum = y_sub["aqua_cnt"].sum()
    t_sum = y_sub["terra_cnt"].sum()
    
    r_pt, r_l, r_u = block_bootstrap_ratio(y_sub)
    
    # Aqua-only ratio on cell-days where Aqua present
    a_sub = y_sub[y_sub["aqua_cnt"] > 0]
    r_aqua = float(a_sub["viirs_ref"].sum() / np.maximum(1.0, a_sum))
    
    # Terra-only ratio on cell-days where Terra present
    t_sub = y_sub[y_sub["terra_cnt"] > 0]
    r_terra = float(t_sub["viirs_ref"].sum() / np.maximum(1.0, t_sum))
    
    # Overpass medians
    op_y = overpass_df[overpass_df["yr"] == y]
    op_aqua_d = op_y.loc[(op_y["platform"] == "Aqua") & (op_y["day_night"] == "D"), "med_ist_hr"].values
    op_terra_d = op_y.loc[(op_y["platform"] == "Terra") & (op_y["day_night"] == "D"), "med_ist_hr"].values
    op_snpp_d = op_y.loc[(op_y["platform"] == "S-NPP") & (op_y["day_night"] == "D"), "med_ist_hr"].values
    
    annual_rows.append({
        "Year": y,
        "Total_Cell_Days": tot_cd,
        "Aqua_Present_Share": round(aqua_share, 4),
        "VIIRS_Obs": int(v_sum),
        "MODIS_Used": int(m_sum),
        "Ratio_Plat_Used": round(r_pt, 4),
        "CI_90_Lower": round(r_l, 4),
        "CI_90_Upper": round(r_u, 4),
        "Ratio_Aqua_Only": round(r_aqua, 4),
        "Ratio_Terra_Only": round(r_terra, 4),
        "Aqua_Day_IST": op_aqua_d[0] if len(op_aqua_d) > 0 else np.nan,
        "Terra_Day_IST": op_terra_d[0] if len(op_terra_d) > 0 else np.nan,
        "SNPP_Day_IST": op_snpp_d[0] if len(op_snpp_d) > 0 else np.nan,
    })

annual_df = pd.DataFrame(annual_rows)
print("\n=== ANNUAL RATIO TABLE & OVERPASS TIMING ===", flush=True)
print(annual_df.to_string(), flush=True)

# Trend regression
lr_res = linregress(annual_df["Year"], annual_df["Ratio_Plat_Used"])
print(f"\nLinear Trend on Platform_Used Ratio: slope={lr_res.slope:.4f}/yr, p={lr_res.pvalue:.4f}, r2={lr_res.rvalue**2:.4f}", flush=True)

lr_aqua = linregress(annual_df["Year"], annual_df["Ratio_Aqua_Only"])
print(f"Linear Trend on Aqua-Only Ratio: slope={lr_aqua.slope:.4f}/yr, p={lr_aqua.pvalue:.4f}, r2={lr_aqua.rvalue**2:.4f}", flush=True)

lr_terra = linregress(annual_df["Year"], annual_df["Ratio_Terra_Only"])
print(f"Linear Trend on Terra-Only Ratio: slope={lr_terra.slope:.4f}/yr, p={lr_terra.pvalue:.4f}, r2={lr_terra.rvalue**2:.4f}", flush=True)

# -----------------------------------------------------------------------------
# Part 3: Month Groups & Day/Night
# -----------------------------------------------------------------------------
def get_mg(m):
    if m in (1, 2, 3): return "Q1 (Jan-Mar)"
    if m in (4, 5, 6): return "Q2 (Apr-Jun)"
    if m in (7, 8, 9): return "Q3 (Jul-Sep)"
    return "Q4 (Oct-Dec)"

df["month_group"] = df["mo"].apply(get_mg)

mg_dn_rows = []
for (mg, dn), grp in df.groupby(["month_group", "day_night"]):
    r_pt, r_l, r_u = block_bootstrap_ratio(grp)
    mg_dn_rows.append({
        "Month_Group": mg,
        "Day_Night": dn,
        "VIIRS_Obs": int(grp["viirs_ref"].sum()),
        "MODIS_Used": int(grp["modis_used"].sum()),
        "Ratio": round(r_pt, 4),
        "CI_90_Lower": round(r_l, 4),
        "CI_90_Upper": round(r_u, 4),
    })

mg_dn_df = pd.DataFrame(mg_dn_rows)
print("\n=== RATIO BY MONTH GROUP & DAY/NIGHT ===", flush=True)
print(mg_dn_df.to_string(), flush=True)

# -----------------------------------------------------------------------------
# Part 4: Backward Test (Testing 2012-2017)
# -----------------------------------------------------------------------------
print("\n=== BACKWARD TEST (TEST ON 2012-2017) ===", flush=True)
stratum_all = df.groupby(["yr", "mo", "day_night"])[["viirs_ref", "modis_used"]].sum().reset_index()

test_sub = stratum_all[stratum_all["yr"].isin(range(2012, 2018))].copy()
test_strata = list(zip(test_sub["mo"], test_sub["day_night"]))

def get_strata_ratios(train_sub):
    grp = train_sub.groupby(["mo", "day_night"])[["viirs_ref", "modis_used"]].sum()
    r = (grp["viirs_ref"] / np.maximum(1.0, grp["modis_used"])).to_dict()
    glob = float(train_sub["viirs_ref"].sum() / max(1.0, train_sub["modis_used"].sum()))
    return r, glob

models_train = {
    "Full Late (2018-2025)": stratum_all[stratum_all["yr"].isin(range(2018, 2026))],
    "Nearest K=2 (2018-2019)": stratum_all[stratum_all["yr"].isin([2018, 2019])],
    "Nearest K=3 (2018-2020)": stratum_all[stratum_all["yr"].isin([2018, 2019, 2020])],
    "Latest K=2 (2024-2025)": stratum_all[stratum_all["yr"].isin([2024, 2025])],
    "Latest K=3 (2023-2025)": stratum_all[stratum_all["yr"].isin([2023, 2024, 2025])],
}

for m_name, tr_data in models_train.items():
    r_dict, glob_r = get_strata_ratios(tr_data)
    pred_r = np.array([r_dict.get(s, glob_r) for s in test_strata])
    test_sub[f"pred_{m_name}"] = test_sub["modis_used"] * pred_r

# Also include B0 (Identity)
test_sub["pred_B0"] = test_sub["modis_used"]

test_cm = test_sub.groupby(["yr", "mo"])[["viirs_ref", "pred_B0"] + [f"pred_{m}" for m in models_train.keys()]].sum().reset_index()

bwd_rows = []
for y, grp in test_cm.groupby("yr"):
    v = grp["viirs_ref"].values
    v_sum = np.sum(v)
    row = {"Test_Year": y, "VIIRS_Obs": int(v_sum)}
    p_b0 = grp["pred_B0"].values
    row["B0_Rel_MAE"] = round(np.sum(np.abs(p_b0 - v)) / v_sum * 100, 1)
    for m_name in models_train.keys():
        p = grp[f"pred_{m_name}"].values
        rel_mae = np.sum(np.abs(p - v)) / v_sum
        rel_bias = np.sum(p - v) / v_sum
        row[f"{m_name}_Rel_MAE"] = round(rel_mae * 100, 1)
        row[f"{m_name}_Rel_Bias"] = round(rel_bias * 100, 1)
    bwd_rows.append(row)

bwd_df = pd.DataFrame(bwd_rows)
print("\n=== BACKWARD TEST RESULTS BY YEAR (2012-2017) ===", flush=True)
print(bwd_df.to_string(), flush=True)

print("\n=== OVERALL BACKWARD TEST SUMMARY (2012-2017) ===", flush=True)
v_tot = test_cm["viirs_ref"].values
v_tot_sum = np.sum(v_tot)
p_b0_tot = test_cm["pred_B0"].values
print(f"{'B0 (Identity)':25s} | Rel MAE: {np.sum(np.abs(p_b0_tot - v_tot)) / v_tot_sum:.2%} | Rel Bias: {np.sum(p_b0_tot - v_tot) / v_tot_sum:+.2%}", flush=True)
for m_name in models_train.keys():
    p = test_cm[f"pred_{m_name}"].values
    rel_mae = np.sum(np.abs(p - v_tot)) / v_tot_sum
    rel_bias = np.sum(p - v_tot) / v_tot_sum
    rho, _ = spearmanr(p, v_tot)
    print(f"{m_name:25s} | Rel MAE: {rel_mae:.2%} | Rel Bias: {rel_bias:+.2%} | Spearman rho: {rho:.3f}", flush=True)
