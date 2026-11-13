"""Recompute leave-one-year-out uncertainty bounds, coverage, and regional vs national models on the corrected single-platform VIIRS reference."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import duckdb
import h3
import numpy as np
import pandas as pd

from app.shared.regions import load_regions


def main():
    con = duckdb.connect("data/slice_2019_2022/terraflare.duckdb", read_only=True)
    
    query = """
        SELECT 
            h3_cell,
            acq_date,
            day_night,
            region_id,
            EXTRACT(year FROM acq_date)::INTEGER as yr,
            EXTRACT(month FROM acq_date)::INTEGER as mo,
            modis_terra_observed,
            modis_aqua_observed,
            viirs_observed
        FROM harmonized_cell_day
        WHERE EXTRACT(year FROM acq_date) BETWEEN 2019 AND 2022
    """
    df = con.execute(query).df()
    print(f"Loaded {len(df):,} cell-day rows across 2019-2022.")

    # Determine modis_used (Aqua if present, else Terra)
    df["modis_used"] = np.where(df["modis_aqua_observed"] > 0, df["modis_aqua_observed"], df["modis_terra_observed"])
    df["stratum"] = df["mo"].astype(str) + "_" + df["day_night"]

    years = [2019, 2020, 2021, 2022]

    # Pre-compute H3 parent cells and lat/lon
    unique_cells = df["h3_cell"].unique()
    res2_map = {c: h3.cell_to_parent(c, 2) for c in unique_cells}
    res3_map = {c: h3.cell_to_parent(c, 3) for c in unique_cells}
    res4_map = {c: h3.cell_to_parent(c, 4) for c in unique_cells}
    
    cell_latlng = {c: h3.cell_to_latlng(c) for c in unique_cells}

    regions = load_regions()
    four_regions = ["north_india", "northeast_india", "southwest_india", "southeast_india"]

    def get_cell_region(c: str) -> str:
        lat, lon = cell_latlng[c]
        for rid in four_regions:
            if regions[rid].bbox.contains(lat, lon):
                return rid
        return "other"

    cell_region_map = {c: get_cell_region(c) for c in unique_cells}

    df["h3_res2"] = df["h3_cell"].map(res2_map)
    df["h3_res3"] = df["h3_cell"].map(res3_map)
    df["h3_res4"] = df["h3_cell"].map(res4_map)
    df["quadrant_region"] = df["h3_cell"].map(cell_region_map)

    # Storage for all evaluated area-months across the 4 LOYO folds
    evaluated_national = []
    evaluated_regional = []

    # Leave-one-year-out loop
    for test_yr in years:
        train_df = df[df["yr"] != test_yr]
        test_df = df[df["yr"] == test_yr].copy()

        # 1. Fit National Stratified Ratio on train_df
        strata_sums = train_df.groupby("stratum")[["viirs_observed", "modis_used"]].sum()
        national_ratios = (strata_sums["viirs_observed"] / np.maximum(1.0, strata_sums["modis_used"])).to_dict()
        global_ratio = float(train_df["viirs_observed"].sum() / max(1.0, train_df["modis_used"].sum()))

        test_df["pred_nat"] = test_df["modis_used"] * test_df["stratum"].map(lambda s: national_ratios.get(s, global_ratio))

        # 2. Fit Regional Stratified Ratio on train_df
        reg_strata = train_df.groupby(["quadrant_region", "stratum"])[["viirs_observed", "modis_used"]].sum()
        reg_ratios = (reg_strata["viirs_observed"] / np.maximum(1.0, reg_strata["modis_used"])).to_dict()

        # Vectorized lookup
        reg_keys = list(zip(test_df["quadrant_region"], test_df["stratum"]))
        reg_r_series = pd.Series([reg_ratios.get(k, national_ratios.get(k[1], global_ratio)) for k in reg_keys], index=test_df.index)
        test_df["pred_reg"] = test_df["modis_used"] * reg_r_series

        # Evaluate across spatial grains
        # A. Country-level
        c_m = test_df.groupby(["yr", "mo"])[["pred_nat", "pred_reg", "viirs_observed"]].sum().reset_index()
        c_m["area_type"] = "country"
        c_m["area_id"] = "india"
        evaluated_national.append(c_m)

        # B. 4-Region level
        for rid in four_regions:
            r_df = test_df[test_df["quadrant_region"] == rid]
            if not r_df.empty:
                r_m = r_df.groupby(["yr", "mo"])[["pred_nat", "pred_reg", "viirs_observed"]].sum().reset_index()
                r_m["area_type"] = "region"
                r_m["area_id"] = rid
                evaluated_national.append(r_m)

        # C. H3 Res 2
        r2_m = test_df.groupby(["h3_res2", "yr", "mo"])[["pred_nat", "pred_reg", "viirs_observed"]].sum().reset_index()
        r2_m["area_type"] = "res2"
        r2_m["area_id"] = r2_m["h3_res2"]
        evaluated_national.append(r2_m[["yr", "mo", "pred_nat", "pred_reg", "viirs_observed", "area_type", "area_id"]])

        # D. H3 Res 3
        r3_m = test_df.groupby(["h3_res3", "yr", "mo"])[["pred_nat", "pred_reg", "viirs_observed"]].sum().reset_index()
        r3_m["area_type"] = "res3"
        r3_m["area_id"] = r3_m["h3_res3"]
        evaluated_national.append(r3_m[["yr", "mo", "pred_nat", "pred_reg", "viirs_observed", "area_type", "area_id"]])

        # E. H3 Res 4
        r4_m = test_df.groupby(["h3_res4", "yr", "mo"])[["pred_nat", "pred_reg", "viirs_observed"]].sum().reset_index()
        r4_m["area_type"] = "res4"
        r4_m["area_id"] = r4_m["h3_res4"]
        evaluated_national.append(r4_m[["yr", "mo", "pred_nat", "pred_reg", "viirs_observed", "area_type", "area_id"]])

    all_eval = pd.concat(evaluated_national, ignore_index=True)
    all_eval = all_eval[(all_eval["pred_nat"] > 0) | (all_eval["viirs_observed"] > 0)].copy()

    # Absolute and Relative Errors for National vs Regional models
    all_eval["abs_err_nat"] = np.abs(all_eval["pred_nat"] - all_eval["viirs_observed"])
    all_eval["abs_err_reg"] = np.abs(all_eval["pred_reg"] - all_eval["viirs_observed"])

    all_eval["rel_err_nat"] = all_eval["abs_err_nat"] / np.maximum(1.0, all_eval["viirs_observed"])
    all_eval["rel_err_reg"] = all_eval["abs_err_reg"] / np.maximum(1.0, all_eval["viirs_observed"])

    print("\n==========================================================================================")
    print("LOYO OUT-OF-SAMPLE COMPARISON: National Stratified Ratio vs Regional Stratified Ratio")
    print("==========================================================================================")
    for atype in ["country", "region", "res2", "res3", "res4"]:
        sub = all_eval[all_eval["area_type"] == atype]
        n_m = len(sub)
        pooled_y = sub["viirs_observed"].sum()
        nat_pooled_rel_mae = sub["abs_err_nat"].sum() / pooled_y * 100.0
        reg_pooled_rel_mae = sub["abs_err_reg"].sum() / pooled_y * 100.0

        nat_mean_rel_mae = sub["rel_err_nat"].mean() * 100.0
        reg_mean_rel_mae = sub["rel_err_reg"].mean() * 100.0

        print(f"Area {atype:7s} (N={n_m:5d}): National Pooled Rel MAE = {nat_pooled_rel_mae:5.2f}% | Regional = {reg_pooled_rel_mae:5.2f}%")
        print(f"                       National Mean Rel MAE   = {nat_mean_rel_mae:5.2f}% | Regional = {reg_mean_rel_mae:5.2f}%\n")

    # Size-dependent uncertainty bounds computation
    # Signed relative deviation: (actual - pred) / pred
    all_eval["signed_rel_dev"] = (all_eval["viirs_observed"] - all_eval["pred_nat"]) / np.maximum(1.0, all_eval["pred_nat"])

    print("==========================================================================================")
    print("RECOMPUTED SIZE-DEPENDENT UNCERTAINTY CLASS BINS (Task 9 Addendum Point A)")
    print("==========================================================================================")

    raw_bins = [
        ("very_small", 0, 10),
        ("small", 10, 50),
        ("medium", 50, 250),
        ("large", 250, 1000),
        ("very_large", 1000, 5000),
        ("macro", 5000, float("inf")),
    ]

    bridge_term = 0.0184  # +/- 1.84%

    class_results = []
    for name, low, high in raw_bins:
        sub = all_eval[(all_eval["pred_nat"] >= low) & (all_eval["pred_nat"] < high)]
        n = len(sub)
        if n == 0:
            continue
        devs = sub["signed_rel_dev"].to_numpy()
        p5 = float(np.percentile(devs, 5))
        p50 = float(np.percentile(devs, 50))
        p95 = float(np.percentile(devs, 95))
        rel_mae = float(sub["rel_err_nat"].mean())

        raw_lower = max(0.0, -p5)
        raw_upper = max(0.0, p95)
        tot_lower = raw_lower + bridge_term
        tot_upper = raw_upper + bridge_term

        # Initial coverage with raw bounds + bridge
        in_interval = (all_eval["viirs_observed"] >= all_eval["pred_nat"] * (1.0 - tot_lower)) & \
                      (all_eval["viirs_observed"] <= all_eval["pred_nat"] * (1.0 + tot_upper))
        cov = float(in_interval[sub.index].mean() * 100.0)

        # Widen bounds if needed to reach within 5 points of 90% (85% <= cov <= 95%)
        adj_lower = tot_lower
        adj_upper = tot_upper
        while cov < 85.0 and adj_upper < 10.0 and name != "very_small":
            adj_lower += 0.01
            adj_upper += 0.05
            in_interval = (all_eval["viirs_observed"] >= all_eval["pred_nat"] * (1.0 - adj_lower)) & \
                          (all_eval["viirs_observed"] <= all_eval["pred_nat"] * (1.0 + adj_upper))
            cov = float(in_interval[sub.index].mean() * 100.0)

        half_width = (adj_lower + adj_upper) / 2.0
        if name == "very_small" or adj_lower is None:
            rel_label = "insufficient"
        elif half_width <= 0.20:
            rel_label = "high"
        elif half_width <= 0.45:
            rel_label = "medium"
        else:
            rel_label = "low"

        class_results.append({
            "name": name,
            "min_expected": low,
            "max_expected": high,
            "n": n,
            "p5": p5,
            "p50": p50,
            "p95": p95,
            "rel_lower": round(adj_lower, 3),
            "rel_upper": round(adj_upper, 3),
            "half_width": round(half_width, 3),
            "reliability": rel_label,
            "rel_mae": round(rel_mae * 100.0, 1),
            "coverage": round(cov, 1),
        })

    res_df = pd.DataFrame(class_results)
    for _, r in res_df.iterrows():
        print(f"| `{r['name']}` | [{r['min_expected']:.0f}, {r['max_expected']:.0f}) | N={r['n']:5d} | Rel Bounds: [{r['rel_lower']:.3f}, {r['rel_upper']:.3f}] | Half-width: {r['half_width']:.3f} | Reliability: `{r['reliability']}` | Coverage: {r['coverage']:.1f}% | Rel MAE: {r['rel_mae']:.1f}% |")


if __name__ == "__main__":
    main()
