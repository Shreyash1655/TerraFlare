"""Benchmark query execution times on the full dataset (data/terraflare.duckdb) for Task 9.

Queries tested:
1. Whole country (India)
2. 4-region bbox (North India, ~66,500 H3 cells)
3. Small polygon (47 H3 cells)

Target SLA: under 2.0 seconds per query.
Also reports the current-vs-median result for India for the latest month with reliability label.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import duckdb

from app.core.analytics.area_monthly import (
    aggregate_area_monthly,
    compute_current_vs_median,
    resolve_area_cells,
)
from app.core.spatial.grid import bbox_to_cells
from app.settings import settings


def run_benchmark():
    db_path = Path("data/terraflare.duckdb")
    if not db_path.exists():
        print(f"Database {db_path} does not exist.")
        return

    con = duckdb.connect(str(db_path), read_only=True)

    print("=================================================================")
    print("BENCHMARK: Area Monthly Aggregation & Current-vs-Median (Task 9)")
    print("Target SLA: < 2.0 seconds per query")
    print("=================================================================\n")

    # 1. Whole Country (India)
    t0 = time.perf_counter()
    df_country = aggregate_area_monthly(cells=None, series="harmonized", con=con)
    t_country = time.perf_counter() - t0
    print(f"1. Whole Country (India):")
    print(f"   Rows returned: {len(df_country)} months")
    print(f"   Execution time: {t_country:.4f} seconds (Target < 2.0s: {'PASS' if t_country < 2.0 else 'FAIL'})")
    if not df_country.empty:
        latest = df_country.iloc[-1]
        print(f"   Latest month in series: {latest['year_month']} | Harmonized value: {latest['harmonized_value']} | Partial: {latest['is_partial_month']} | Provisional: {latest['is_provisional']}")
    print()

    # 2. 4-Region Bounding Box (North India: [73.0, 24.0, 89.0, 37.0])
    north_bbox = (73.0, 24.0, 89.0, 37.0)
    cells_north = list(bbox_to_cells(north_bbox, resolution=6))
    t0 = time.perf_counter()
    df_north = aggregate_area_monthly(cells=cells_north, series="harmonized", con=con)
    t_north = time.perf_counter() - t0
    print(f"2. 4-Region BBox (North India, {len(cells_north):,} cells):")
    print(f"   Rows returned: {len(df_north)} months")
    print(f"   Execution time: {t_north:.4f} seconds (Target < 2.0s: {'PASS' if t_north < 2.0 else 'FAIL'})")
    print()

    # 3. Small Polygon (Punjab/Haryana agricultural zone: ~47 cells)
    small_poly = {
        "type": "Polygon",
        "coordinates": [[
            [75.0, 30.0],
            [75.4, 30.0],
            [75.4, 30.3],
            [75.0, 30.3],
            [75.0, 30.0],
        ]]
    }
    _, cells_poly = resolve_area_cells(polygon=small_poly, h3_res=6)
    t0 = time.perf_counter()
    df_poly = aggregate_area_monthly(cells=cells_poly, series="harmonized", con=con)
    t_poly = time.perf_counter() - t0
    print(f"3. Small Polygon ({len(cells_poly)} cells):")
    print(f"   Rows returned: {len(df_poly)} months")
    print(f"   Execution time: {t_poly:.4f} seconds (Target < 2.0s: {'PASS' if t_poly < 2.0 else 'FAIL'})")
    print()

    # 4. Current-vs-Median for India (Latest Month)
    t0 = time.perf_counter()
    cvm = compute_current_vs_median(cells=None, series="harmonized", con=con)
    t_cvm = time.perf_counter() - t0
    print("4. Current-vs-Median for India (Latest Month):")
    print(f"   Execution time: {t_cvm:.4f} seconds (Target < 2.0s: {'PASS' if t_cvm < 2.0 else 'FAIL'})")
    print(f"   Target Period: {cvm['year']}-{cvm['month']:02d} (is_partial={cvm['is_partial']}, is_provisional={cvm['is_provisional']})")
    print(f"   Current Value: {cvm['current']:,}")
    print(f"   Baseline Median: {cvm['median']:,}")
    print(f"   Baseline Q25: {cvm['q25']:,} | Q75: {cvm['q75']:,}")
    print(f"   Ratio to Median: {cvm['ratio']} ({cvm['ratio']:.3f}x)")
    print(f"   Empirical Percentile: {cvm['percentile']}%")
    print(f"   Baseline Years Count: {cvm['n_baseline_years']} years (complete non-provisional years)")
    print(f"   Uncertainty Interval: [{cvm['lower']:,}, {cvm['upper']:,}]")
    print(f"   Reliability Label: {cvm['reliability']}")
    print(f"   Warning: {cvm['warning']}")
    print("=================================================================")


if __name__ == "__main__":
    run_benchmark()
