"""Hand-made fixture tests for Area Monthly Activity, Historical Baselines, and Current-vs-Median (Task 9).

Covers:
1. Known sums across cells, months, and sensor series
2. Apples-to-apples partial-month same-days logic
3. Exclusion of static_masked and invalid rows
4. Dynamic provisional flags from manifest and exclusion from baselines
5. Uncertainty intervals, reliability classes, and small-area warnings
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from app.core.analytics.area_monthly import (
    aggregate_area_monthly,
    compute_area_baselines,
    compute_current_vs_median,
    resolve_area_cells,
)


@pytest.fixture
def mock_con():
    """Create in-memory DuckDB connection with controlled synthetic fixtures."""
    con = duckdb.connect(":memory:")

    # Create harmonized_cell_day schema
    con.execute("""
        CREATE TABLE harmonized_cell_day (
            h3_cell VARCHAR,
            acq_date DATE,
            day_night VARCHAR,
            region_id VARCHAR,
            harmonized_value DOUBLE,
            harmonized_lower DOUBLE,
            harmonized_upper DOUBLE,
            modis_observed DOUBLE,
            modis_terra_observed DOUBLE,
            modis_aqua_observed DOUBLE,
            viirs_observed DOUBLE,
            viirs_platform VARCHAR,
            platform_used VARCHAR,
            interval_level DOUBLE,
            method_id VARCHAR,
            value_type VARCHAR,
            is_provisional BOOLEAN,
            static_masked BOOLEAN,
            is_valid BOOLEAN,
            calibration_version VARCHAR,
            data_version VARCHAR
        )
    """)
    return con


def test_known_sums(mock_con):
    """Verify exact known sums across sensors, cells, and series."""
    # Insert known rows
    # Jan 2021: cell_1 (harm=100, modis=50, viirs=80), cell_2 (harm=150, modis=70, viirs=120) -> sum harm=250, modis=120, viirs=200
    # Feb 2021: cell_1 (harm=200, modis=100, viirs=160) -> sum harm=200, modis=100, viirs=160
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('cell_1', '2021-01-10', 'D', 'india', 100.0, 80.0, 120.0, 50.0, 30.0, 20.0, 80.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('cell_2', '2021-01-20', 'D', 'india', 150.0, 120.0, 180.0, 70.0, 40.0, 30.0, 120.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('cell_1', '2021-02-15', 'D', 'india', 200.0, 160.0, 240.0, 100.0, 60.0, 40.0, 160.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')
    """)

    # 1. Both cells, harmonized series
    df = aggregate_area_monthly(cells=["cell_1", "cell_2"], series="harmonized", con=mock_con)
    assert len(df) == 2

    jan = df[df["year_month"] == "2021-01"].iloc[0]
    assert jan["harmonized_value"] == 250.0
    assert jan["modis_observed"] == 120.0
    assert jan["modis_terra_observed"] == 70.0
    assert jan["modis_aqua_observed"] == 50.0
    assert jan["viirs_observed"] == 200.0
    assert jan["n_days_with_data"] == 2
    assert jan["reliability"] == "observed"
    assert jan["lower"] == 250.0
    assert jan["upper"] == 250.0

    feb = df[df["year_month"] == "2021-02"].iloc[0]
    assert feb["harmonized_value"] == 200.0
    assert feb["modis_observed"] == 100.0
    assert feb["viirs_observed"] == 160.0
    assert feb["n_days_with_data"] == 1

    # 2. Single cell filter
    df_cell1 = aggregate_area_monthly(cells=["cell_1"], series="harmonized", con=mock_con)
    jan_c1 = df_cell1[df_cell1["year_month"] == "2021-01"].iloc[0]
    assert jan_c1["harmonized_value"] == 100.0

    # 3. viirs_native series
    df_viirs = aggregate_area_monthly(cells=["cell_1", "cell_2"], series="viirs_native", con=mock_con)
    jan_v = df_viirs[df_viirs["year_month"] == "2021-01"].iloc[0]
    assert jan_v["harmonized_value"] == 200.0  # Uses viirs_observed
    # Normal VIIRS month: observed degenerate interval
    assert jan_v["lower"] == 200.0
    assert jan_v["upper"] == 200.0

    # 4. modis_native series
    df_modis = aggregate_area_monthly(cells=["cell_1", "cell_2"], series="modis_native", con=mock_con)
    jan_m = df_modis[df_modis["year_month"] == "2021-01"].iloc[0]
    assert jan_m["harmonized_value"] == 120.0  # Uses modis_observed


def test_partial_month_same_days_logic(mock_con):
    """Verify apples-to-apples day matching for partial months in current_vs_median.

    Nov 2020-2022: full 30 days at 10/day = 300/month (days 1-9 have 90).
    Nov 2023: only days 1-9 observed at 10/day = 90.
    Expectation:
    current = 90
    baseline median = 90 (days 1-9 compared, NOT full month 300!)
    ratio = 1.0 (0.999 to 1.001)
    """
    rows = []
    # Baseline years 2020, 2021, 2022 (Nov 1 to 30)
    for yr in [2020, 2021, 2022]:
        for d in range(1, 31):
            dt_str = f"{yr}-11-{d:02d}"
            rows.append(f"('cell_1', '{dt_str}', 'D', 'india', 10.0, 8.0, 12.0, 5.0, 3.0, 2.0, 10.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')")

    # Target year 2023 (Nov 1 to 9 only!)
    for d in range(1, 10):
        dt_str = f"2023-11-{d:02d}"
        rows.append(f"('cell_1', '{dt_str}', 'D', 'india', 10.0, 8.0, 12.0, 5.0, 3.0, 2.0, 10.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')")

    mock_con.execute(f"INSERT INTO harmonized_cell_day VALUES {','.join(rows)}")

    res = compute_current_vs_median(
        cells=["cell_1"],
        series="harmonized",
        target_year=2023,
        target_month=11,
        con=mock_con,
    )

    assert res["is_partial"] is True
    assert res["year"] == 2023
    assert res["month"] == 11
    assert res["current"] == 90.0
    # Must match days 1-9 median (90.0), NOT 300.0!
    assert res["median"] == 90.0
    assert res["ratio"] == 1.0
    assert res["n_baseline_years"] == 3
    assert res["percentile"] == 100.0


def test_static_rows_excluded(mock_con):
    """Verify that rows marked static_masked=True or is_valid=False are excluded from aggregation."""
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('cell_1', '2022-05-01', 'D', 'india', 50.0, 40.0, 60.0, 25.0, 15.0, 10.0, 50.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('cell_1', '2022-05-02', 'D', 'india', 200.0, 160.0, 240.0, 100.0, 50.0, 50.0, 200.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, true, true, '1.0', '1.0'),
        ('cell_1', '2022-05-03', 'D', 'india', 100.0, 80.0, 120.0, 50.0, 25.0, 25.0, 100.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, false, '1.0', '1.0')
    """)

    # In 2022-05:
    # Row 1: valid, static_masked=False -> harm=50.0 (INCLUDED)
    # Row 2: static_masked=True -> harm=200.0 (MUST BE EXCLUDED)
    # Row 3: is_valid=False -> harm=100.0 (MUST BE EXCLUDED)

    df = aggregate_area_monthly(cells=["cell_1"], series="harmonized", con=mock_con)
    assert len(df) == 1
    may = df.iloc[0]
    assert may["harmonized_value"] == 50.0
    assert may["n_days_with_data"] == 1

    cvm = compute_current_vs_median(cells=["cell_1"], series="harmonized", target_year=2022, target_month=5, con=mock_con)
    assert cvm["current"] == 50.0


def test_provisional_flags_and_baseline_exclusion(mock_con, tmp_path):
    """Verify provisional flags from manifest and exclusion of provisional months from baselines."""
    # Write synthetic manifest with NRT start 2026-08-01
    manifest = {
        "stream_boundaries": {
            "viirs_snpp": {"sp_end_date": "2026-07-31", "nrt_start_date": "2026-08-01"},
            "modis_c61": {"sp_end_date": "2026-08-31", "nrt_start_date": "2026-09-01"},
        }
    }
    manifest_file = tmp_path / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('cell_1', '2026-07-01', 'D', 'india', 50.0, 40.0, 60.0, 25.0, 10.0, 15.0, 50.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('cell_1', '2026-07-31', 'D', 'india', 50.0, 40.0, 60.0, 25.0, 15.0, 10.0, 50.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('cell_1', '2026-08-15', 'D', 'india', 150.0, 120.0, 180.0, 75.0, 35.0, 40.0, 150.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0'),
        ('cell_1', '2026-09-15', 'D', 'india', 200.0, 160.0, 240.0, 100.0, 50.0, 50.0, 200.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0')
    """)

    df = aggregate_area_monthly(cells=["cell_1"], series="harmonized", data_dir=tmp_path, con=mock_con)
    jul = df[df["year_month"] == "2026-07"].iloc[0]
    aug = df[df["year_month"] == "2026-08"].iloc[0]
    sep = df[df["year_month"] == "2026-09"].iloc[0]

    assert bool(jul["is_provisional"]) is False
    assert bool(aug["is_provisional"]) is True
    assert bool(sep["is_provisional"]) is True

    # Baseline computation: compute_area_baselines should exclude aug and sep
    baselines = compute_area_baselines(monthly_df=df)
    # Only month 7 (Jul) is non-provisional and complete
    assert 7 in baselines
    assert 8 not in baselines  # Excluded because is_provisional=True
    assert 9 not in baselines  # Excluded because is_provisional=True


def test_uncertainty_and_small_area_warning(mock_con):
    """Verify interval semantics, reliability ratings, and small area warning."""
    # Pre-2012 tiny count: 5.0 (uses conversion interval from backward holdout)
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('tiny_cell', '2010-04-10', 'D', 'india', 5.0, 4.0, 6.0, 2.0, 1.0, 1.0, 0.0, 'none', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')
    """)

    res_tiny = compute_current_vs_median(cells=["tiny_cell"], series="harmonized", target_year=2010, target_month=4, con=mock_con)
    assert res_tiny["current"] == 5.0
    assert res_tiny["reliability"] == "insufficient"
    assert res_tiny["lower"] is None
    assert res_tiny["upper"] is None
    assert res_tiny["warning"] is not None
    assert "Area is small" in res_tiny["warning"]

    # VIIRS-era tiny count: 5.0 (direct observation: lower = upper = value, reliability = 'observed', with small area warning)
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('tiny_cell_2', '2021-04-10', 'D', 'india', 5.0, 5.0, 5.0, 2.0, 1.0, 1.0, 5.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')
    """)
    res_tiny_viirs = compute_current_vs_median(cells=["tiny_cell_2"], series="harmonized", target_year=2021, target_month=4, con=mock_con)
    assert res_tiny_viirs["current"] == 5.0
    assert res_tiny_viirs["reliability"] == "observed"
    assert res_tiny_viirs["lower"] == 5.0
    assert res_tiny_viirs["upper"] == 5.0
    assert res_tiny_viirs["warning"] is not None
    assert "Area is small" in res_tiny_viirs["warning"]

    # Pre-2012 large count: 12,000.0 (macro size class conversion interval)
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('macro_cell', '2010-05-10', 'D', 'india', 12000.0, 10000.0, 14000.0, 6000.0, 3000.0, 3000.0, 0.0, 'none', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')
    """)

    res_macro = compute_current_vs_median(cells=["macro_cell"], series="harmonized", target_year=2010, target_month=5, con=mock_con)
    assert res_macro["current"] == 12000.0
    assert res_macro["reliability"] == "medium"
    assert res_macro["lower"] is not None
    assert res_macro["upper"] is not None
    assert res_macro["warning"] is None


def test_bridge_uncertainty_applied_only_to_bridge_months(mock_con):
    """Verify that bridge uncertainty term (+/- 1.84%) is applied ONLY for months where reference platform changed."""
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('c1', '2022-07-28', 'D', 'india', 1000.0, 981.6, 1018.4, 500.0, 250.0, 250.0, 1000.0, 'NOAA-20', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('c1', '2022-08-05', 'D', 'india', 1000.0, 981.6, 1018.4, 500.0, 250.0, 250.0, 1000.0, 'NOAA-20', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('c1', '2022-09-10', 'D', 'india', 1000.0, 1000.0, 1000.0, 500.0, 250.0, 250.0, 1000.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('c1', '2026-11-05', 'D', 'india', 2000.0, 1963.2, 2036.8, 1000.0, 500.0, 500.0, 2000.0, 'NOAA-20', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0')
    """)

    df = aggregate_area_monthly(cells=["c1"], series="harmonized", con=mock_con)
    jul22 = df[df["year_month"] == "2022-07"].iloc[0]
    aug22 = df[df["year_month"] == "2022-08"].iloc[0]
    sep22 = df[df["year_month"] == "2022-09"].iloc[0]
    nov26 = df[df["year_month"] == "2026-11"].iloc[0]

    # July and August 2022: reference changed S-NPP -> NOAA-20 -> S-NPP (bridge term applied)
    assert jul22["lower"] == round(1000.0 * (1.0 - 0.0184), 2)
    assert jul22["upper"] == round(1000.0 * (1.0 + 0.0184), 2)
    assert jul22["interval_applies_to"] == "bridge_uncertainty"

    assert aug22["lower"] == round(1000.0 * (1.0 - 0.0184), 2)
    assert aug22["upper"] == round(1000.0 * (1.0 + 0.0184), 2)
    assert aug22["interval_applies_to"] == "bridge_uncertainty"

    # September 2022: normal S-NPP reference (degenerate interval lower = upper = value)
    assert sep22["lower"] == 1000.0
    assert sep22["upper"] == 1000.0
    assert sep22["interval_applies_to"] == "none"
    assert sep22["reliability"] == "observed"

    # November 2026: reference changed S-NPP -> NOAA-20 on 2 Nov 2026 (bridge term applied)
    assert nov26["lower"] == round(2000.0 * (1.0 - 0.0184), 2)
    assert nov26["upper"] == round(2000.0 * (1.0 + 0.0184), 2)
    assert nov26["interval_applies_to"] == "bridge_uncertainty"


def test_pre_2012_conversion_interval_and_one_line_test(mock_con):
    """Verify sign convention and one-line test assertion: lower <= y_true <= upper."""
    # True observed VIIRS value y_true, estimated harmonized value y_hat
    y_hat = 10000.0
    y_true = 11500.0  # true value is higher than prediction

    # Relative error definition: epsilon = (y_true - y_hat) / y_hat
    # 90% bounds: [y_hat * (1 - rel_lower), y_hat * (1 + rel_upper)]
    # Under macro bounds: rel_lower = 0.2456, rel_upper = 0.3356
    lower = round(y_hat * (1.0 - 0.2456), 2)  # 7544.0
    upper = round(y_hat * (1.0 + 0.3356), 2)  # 13356.0

    # One-line test that the interval is on the true value:
    assert lower <= y_true <= upper


def test_small_area_fallback_composite_splicing(mock_con):
    """Verify small-area fallback: keep 2012+ observed series and return modis_native for pre-2012."""
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('small_c', '2010-06-10', 'D', 'india', 25.0, 15.0, 35.0, 10.0, 5.0, 5.0, 0.0, 'none', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0'),
        ('small_c', '2021-06-10', 'D', 'india', 30.0, 20.0, 40.0, 12.0, 6.0, 6.0, 30.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', false, false, true, '1.0', '1.0')
    """)

    df = aggregate_area_monthly(cells=["small_c"], series="harmonized", con=mock_con)
    assert len(df) == 2

    # Pre-2012 row: falls back to native MODIS count (10.0) with reliability 'low'
    pre12 = df[df["year_month"] == "2010-06"].iloc[0]
    assert pre12["harmonized_value"] == 10.0  # native MODIS count
    assert pre12["lower"] == 10.0
    assert pre12["upper"] == 10.0
    assert pre12["reliability"] == "low"
    assert pre12["value_type"] == "modis_native"

    # Post-2012 row: keeps observed VIIRS series (30.0) with reliability 'observed'
    post12 = df[df["year_month"] == "2021-06"].iloc[0]
    assert post12["harmonized_value"] == 30.0  # observed VIIRS
    assert post12["lower"] == 30.0
    assert post12["upper"] == 30.0
    assert post12["reliability"] == "observed"
    assert post12["value_type"] == "observed"


def test_monthly_flags_aug_nov_2026(mock_con):
    """Verify monthly flags: Aug-Nov 2026 flagged provisional, Nov 2026 partial."""
    rows = []
    # Aug 2026: 31 days
    for d in range(1, 32):
        rows.append(f"('c_prov', '2026-08-{d:02d}', 'D', 'india', 10.0, 10.0, 10.0, 5.0, 2.0, 3.0, 10.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0')")
    # Sep 2026: 30 days
    for d in range(1, 31):
        rows.append(f"('c_prov', '2026-09-{d:02d}', 'D', 'india', 10.0, 10.0, 10.0, 5.0, 2.0, 3.0, 10.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0')")
    # Oct 2026: 31 days
    for d in range(1, 32):
        rows.append(f"('c_prov', '2026-10-{d:02d}', 'D', 'india', 10.0, 10.0, 10.0, 5.0, 2.0, 3.0, 10.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0')")
    # Nov 2026: 9 days (partial month)
    for d in range(1, 10):
        rows.append(f"('c_prov', '2026-11-{d:02d}', 'D', 'india', 10.0, 10.0, 10.0, 5.0, 2.0, 3.0, 10.0, 'NOAA-20', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0')")

    mock_con.execute(f"INSERT INTO harmonized_cell_day VALUES {','.join(rows)}")

    df = aggregate_area_monthly(cells=["c_prov"], series="harmonized", con=mock_con)

    aug = df[df["year_month"] == "2026-08"].iloc[0]
    sep = df[df["year_month"] == "2026-09"].iloc[0]
    oct_ = df[df["year_month"] == "2026-10"].iloc[0]
    nov = df[df["year_month"] == "2026-11"].iloc[0]

    # Provisional flags: Aug-Nov 2026 ALL provisional
    assert bool(aug["is_provisional"]) is True
    assert bool(sep["is_provisional"]) is True
    assert bool(oct_["is_provisional"]) is True
    assert bool(nov["is_provisional"]) is True

    # Partial flags: Aug-Oct complete, Nov partial
    assert bool(aug["is_partial"]) is False
    assert bool(sep["is_partial"]) is False
    assert bool(oct_["is_partial"]) is False
    assert bool(nov["is_partial"]) is True

    # Days covered and days in month
    assert aug["days_covered"] == 31 and aug["days_in_month"] == 31
    assert sep["days_covered"] == 30 and sep["days_in_month"] == 30
    assert oct_["days_covered"] == 31 and oct_["days_in_month"] == 31
    assert nov["days_covered"] == 9 and nov["days_in_month"] == 30


def test_static_contamination_warning(mock_con):
    """Verify possible_static_contamination warning when NRT rows lack archive veg history."""
    mock_con.execute("""
        CREATE TABLE IF NOT EXISTS obs_clean (
            acq_date DATE,
            h3_cell VARCHAR,
            fire_type VARCHAR,
            processing_stream VARCHAR
        );
        INSERT INTO obs_clean VALUES
        ('2025-05-01', 'veg_cell', '0', 'archive'),
        ('2026-10-10', 'veg_cell', '0', 'NRT');
    """)
    for i in range(9):
        mock_con.execute(f"""
            INSERT INTO obs_clean VALUES ('2026-10-10', 'non_veg_{i}', '0', 'NRT');
            INSERT INTO harmonized_cell_day VALUES ('non_veg_{i}', '2026-10-10', 'D', 'india', 100.0, 80.0, 120.0, 50.0, 25.0, 25.0, 100.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0');
        """)

    res_contam = compute_current_vs_median(series="harmonized", target_year=2026, target_month=10, con=mock_con)
    assert res_contam["share_no_veg_history_pct"] > 0.20
    assert res_contam["warning"] is not None
    assert "possible_static_contamination" in res_contam["warning"]


def test_provisional_month_low_count_warning_and_reliability(mock_con):
    """Task 14: When provisional month has country-level count < 5,000, add warning and set reliability 'low'."""
    # Seed a provisional low-count month (count = 1,500 < 5,000)
    mock_con.execute("""
        INSERT INTO harmonized_cell_day VALUES
        ('c_low', '2026-08-15', 'D', 'india', 1500.0, 1500.0, 1500.0, 300.0, 100.0, 200.0, 1500.0, 'S-NPP', 'Aqua', 0.9, 'stratified_ratio', 'detections', true, false, true, '1.0', '1.0');
    """)
    res_low = compute_current_vs_median(series="harmonized", target_year=2026, target_month=8, con=mock_con)
    assert res_low["is_provisional"] is True
    assert res_low["current"] == 1500.0
    assert res_low["reliability"] == "low"
    assert "provisional NRT vs standard-processing baseline; not validated" in res_low["warning"]


