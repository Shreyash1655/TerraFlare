"""Script to evaluate candidate calibrations under forward and backward holdouts.
Task 8b Item 1, 2, 3, 5, 6.
"""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

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
    CASE WHEN aqua_cnt > 0 THEN aqua_cnt ELSE terra_cnt END AS modis_used,
    aqua_cnt,
    terra_cnt
FROM cell_days
"""
print("Loading cell-day matrix...")
df = con.execute(query).df()
print(f"Loaded {len(df):,} cell-days across 2012-2025.")

# Aggregate to stratum-year level: (yr, mo, day_night)
stratum_year = df.groupby(["yr", "mo", "day_night"])[["viirs_ref", "modis_used", "aqua_cnt", "terra_cnt"]].sum().reset_index()

# Forward test: rolling origin Y in 2016..2025
years = sorted(stratum_year["yr"].unique())
print("Years available:", years)

def evaluate_models(train_df, test_df, k_vals=[2, 3]):
    # Train fixed ratio (Model A)
    # Stratum ratio
    tr_grouped = train_df.groupby(["mo", "day_night"])[["viirs_ref", "modis_used"]].sum()
    fixed_ratios = (tr_grouped["viirs_ref"] / np.maximum(1.0, tr_grouped["modis_used"])).to_dict()
    global_ratio = float(train_df["viirs_ref"].sum() / np.maximum(1.0, train_df["modis_used"].sum()))
    
    # Train K-nearest ratios (Model B)
    k_ratios = {}
    train_years = sorted(train_df["yr"].unique())
    for k in k_vals:
        recent_years = train_years[-k:] if len(train_years) >= k else train_years
        k_sub = train_df[train_df["yr"].isin(recent_years)]
        k_grp = k_sub.groupby(["mo", "day_night"])[["viirs_ref", "modis_used"]].sum()
        k_ratios[k] = (k_grp["viirs_ref"] / np.maximum(1.0, k_grp["modis_used"])).to_dict()

    # Train log-ratio trend (Model C)
    # For each stratum, fit log(ratio) vs yr
    trend_models = {}
    for (m, dn), grp in train_df.groupby(["mo", "day_night"]):
        # Year ratios
        yr_grp = grp.groupby("yr")[["viirs_ref", "modis_used"]].sum()
        valid = (yr_grp["modis_used"] > 0) & (yr_grp["viirs_ref"] > 0)
        if valid.sum() >= 3:
            y_ratios = (yr_grp.loc[valid, "viirs_ref"] / yr_grp.loc[valid, "modis_used"]).values
            xs = yr_grp.loc[valid].index.values.astype(float)
            log_ys = np.log(y_ratios)
            slope, intercept = np.polyfit(xs, log_ys, 1)
            # Clip slope to prevent crazy explosive extrapolation: max 10% change per year (-0.10 to +0.10)
            slope = np.clip(slope, -0.10, 0.10)
            trend_models[(m, dn)] = (slope, intercept)
        else:
            trend_models[(m, dn)] = None

    # Predict on test_df
    preds = {}
    test_df = test_df.copy()
    test_strata = list(zip(test_df["mo"], test_df["day_night"]))
    
    # Model A: Fixed
    r_a = np.array([fixed_ratios.get(s, global_ratio) for s in test_strata])
    test_df["pred_A"] = test_df["modis_used"] * r_a
    
    # Model B: K=2, 3
    for k in k_vals:
        r_b = np.array([k_ratios[k].get(s, global_ratio) for s in test_strata])
        test_df[f"pred_B_k{k}"] = test_df["modis_used"] * r_b
        
    # Model C: Trend
    r_c_list = []
    for (m, dn), yr in zip(test_strata, test_df["yr"]):
        tm = trend_models.get((m, dn))
        if tm is not None:
            slope, intercept = tm
            pred_ratio = np.exp(intercept + slope * float(yr))
            # Clip ratio between 1.0 and 100.0
            pred_ratio = np.clip(pred_ratio, 1.0, 100.0)
            r_c_list.append(pred_ratio)
        else:
            r_c_list.append(fixed_ratios.get((m, dn), global_ratio))
    test_df["pred_C"] = test_df["modis_used"] * np.array(r_c_list)
    
    # Model B0: Identity
    test_df["pred_B0"] = test_df["modis_used"]

    # Aggregate to Country-Month: (yr, mo)
    cm = test_df.groupby(["yr", "mo"])[["viirs_ref", "pred_B0", "pred_A", "pred_B_k2", "pred_B_k3", "pred_C"]].sum().reset_index()
    
    return cm

# 1. Forward test rolling origin: Y in 2016..2025
forward_results = []
for Y in range(2016, 2026):
    train_sub = stratum_year[stratum_year["yr"] < Y]
    test_sub = stratum_year[stratum_year["yr"] == Y]
    cm = evaluate_models(train_sub, test_sub, k_vals=[2, 3])
    forward_results.append(cm)

fwd_df = pd.concat(forward_results, ignore_index=True)

print("\n=== FORWARD TEST (ROLLING ORIGIN) BY TEST YEAR ===")
for Y, grp in fwd_df.groupby("yr"):
    v = grp["viirs_ref"].to_numpy()
    sum_v = np.sum(v)
    res = {"Year": Y, "VIIRS_Obs": int(sum_v)}
    for col, name in [("pred_B0", "B0_Ident"), ("pred_A", "ModA_Fixed"), ("pred_B_k2", "ModB_k2"), ("pred_B_k3", "ModB_k3"), ("pred_C", "ModC_Trend")]:
        p = grp[col].to_numpy()
        rel_mae = np.sum(np.abs(p - v)) / sum_v
        bias = np.mean(p - v)
        rel_bias = np.sum(p - v) / sum_v
        res[f"{name}_rel_mae"] = f"{rel_mae:.1%}"
        res[f"{name}_bias"] = f"{rel_bias:+.1%}"
    print(res)

print("\n=== OVERALL FORWARD TEST SUMMARY (2016-2025) ===")
v_all = fwd_df["viirs_ref"].to_numpy()
sum_v_all = np.sum(v_all)
for col, name in [("pred_B0", "B0 (Identity)"), ("pred_A", "Model A (Fixed all prior)"), ("pred_B_k2", "Model B (Nearest K=2)"), ("pred_B_k3", "Model B (Nearest K=3)"), ("pred_C", "Model C (Log Trend)")]:
    p = fwd_df[col].to_numpy()
    rel_mae = np.sum(np.abs(p - v_all)) / sum_v_all
    rel_bias = np.sum(p - v_all) / sum_v_all
    corr, _ = spearmanr(p, v_all)
    print(f"{name:30s} | Rel MAE: {rel_mae:.2%} | Rel Bias: {rel_bias:+.2%} | Spearman rho: {corr:.3f}")

