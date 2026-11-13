"""Unit and integration tests for Task 7 & 7b: Harmonization Calibration, Uncertainty, and Audit."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from app.core.cleaning.static_mask import (
    build_static_source_mask,
    compute_static_mask_metrics,
    get_static_mask_config,
)
from app.core.harmonization.calibration import (
    BridgeInfo,
    CalibrationSuite,
    ModelMetrics,
    PlatformCalibrationModel,
    apply_calibration_to_cell_days,
    bridge_snpp_and_noaa20,
    build_training_universe,
    create_cell_day_matrix,
    evaluate_monthly_metrics,
    fit_calibration_suite,
    fit_joint_model,
    fit_platform_model,
    prepare_calibration_data,
    save_calibration_models_mart,
)
from app.core.harmonization.uncertainty import (
    compute_block_bootstrap_ratios,
    compute_observed_interval,
    compute_prediction_interval,
    get_uncertainty_config,
)
from app.core.pipeline import stage_clean, stage_harmonize
from app.core.storage.duckdb_repo import DuckDBRepository
from app.core.storage.parquet_io import sync_duckdb_views, write_mart
from app.shared.canonical import CANONICAL_COLUMNS


@pytest.fixture
def sample_obs_clean() -> pd.DataFrame:
    """Generate a clean synthetic dataset covering multiple platforms, months, and streams."""
    base_date = date(2023, 1, 1)
    rows = []
    cell_ids = ["866189247ffffff", "86618924fffffff", "866189257ffffff"]

    # Generate 60 days of data across 2 months
    for day_offset in range(60):
        cur_date = base_date + timedelta(days=day_offset)

        for c_idx, cell in enumerate(cell_ids):
            # Terra (SP, valid)
            rows.append({
                "obs_id": f"terra_{day_offset}_{c_idx}",
                "source_id": "modis_c61",
                "sensor_family": "MODIS",
                "platform": "Terra",
                "processing_stream": "SP",
                "product_version": "6.1",
                "ingest_batch_id": "batch_1",
                "acq_date": cur_date,
                "local_date": cur_date,
                "lat": 28.0 + c_idx * 0.1,
                "lon": 77.0 + c_idx * 0.1,
                "is_valid": True,
                "qc_flags": "",
                "is_synthetic": True,
                "h3_cell": cell,
                "day_night": "D",
                "fire_type": "0",
            })

            # Aqua (SP, valid - active from day 10 onwards to test Aqua-absent period)
            if day_offset >= 10:
                rows.append({
                    "obs_id": f"aqua_{day_offset}_{c_idx}",
                    "source_id": "modis_c61",
                    "sensor_family": "MODIS",
                    "platform": "Aqua",
                    "processing_stream": "SP",
                    "product_version": "6.1",
                    "ingest_batch_id": "batch_1",
                    "acq_date": cur_date,
                    "local_date": cur_date,
                    "lat": 28.0 + c_idx * 0.1,
                    "lon": 77.0 + c_idx * 0.1,
                    "is_valid": True,
                    "qc_flags": "",
                    "is_synthetic": True,
                    "h3_cell": cell,
                    "day_night": "D",
                    "fire_type": "0",
                })

            # S-NPP (SP, active for first 45 days)
            if day_offset < 45:
                for rep in range(2):  # 2 VIIRS detections per MODIS detection
                    rows.append({
                        "obs_id": f"snpp_{day_offset}_{c_idx}_{rep}",
                        "source_id": "viirs_snpp",
                        "sensor_family": "VIIRS",
                        "platform": "S-NPP",
                        "processing_stream": "SP",
                        "product_version": "2.0",
                        "ingest_batch_id": "batch_1",
                        "acq_date": cur_date,
                        "local_date": cur_date,
                        "lat": 28.0 + c_idx * 0.1,
                        "lon": 77.0 + c_idx * 0.1,
                        "is_valid": True,
                        "qc_flags": "",
                        "is_synthetic": True,
                        "h3_cell": cell,
                        "day_night": "D",
                        "fire_type": "0",
                    })

            # NOAA-20 (SP, active from day 15 onwards -> overlap is days 15..44)
            if day_offset >= 15:
                for rep in range(2):
                    rows.append({
                        "obs_id": f"noaa20_{day_offset}_{c_idx}_{rep}",
                        "source_id": "viirs_noaa20",
                        "sensor_family": "VIIRS",
                        "platform": "NOAA-20",
                        "processing_stream": "SP",
                        "product_version": "2.0",
                        "ingest_batch_id": "batch_1",
                        "acq_date": cur_date,
                        "local_date": cur_date,
                        "lat": 28.0 + c_idx * 0.1,
                        "lon": 77.0 + c_idx * 0.1,
                        "is_valid": True,
                        "qc_flags": "",
                        "is_synthetic": True,
                        "h3_cell": cell,
                        "day_night": "D",
                        "fire_type": "0",
                    })

    # Add rows to test filtering rules:
    # 1. NRT row (should be excluded from calibration)
    rows.append({
        "obs_id": "nrt_row_1",
        "source_id": "viirs_snpp",
        "sensor_family": "VIIRS",
        "platform": "S-NPP",
        "processing_stream": "NRT",
        "product_version": "2.0",
        "ingest_batch_id": "batch_nrt",
        "acq_date": date(2023, 1, 10),
        "local_date": date(2023, 1, 10),
        "lat": 28.0,
        "lon": 77.0,
        "is_valid": True,
        "qc_flags": "",
        "is_synthetic": True,
        "h3_cell": cell_ids[0],
        "day_night": "D",
        "fire_type": "0",
    })

    # 2. Row flagged possible_static_source (should be excluded from calibration)
    rows.append({
        "obs_id": "static_flagged_row",
        "source_id": "modis_c61",
        "sensor_family": "MODIS",
        "platform": "Terra",
        "processing_stream": "SP",
        "product_version": "6.1",
        "ingest_batch_id": "batch_1",
        "acq_date": date(2023, 1, 10),
        "local_date": date(2023, 1, 10),
        "lat": 28.0,
        "lon": 77.0,
        "is_valid": True,
        "qc_flags": "possible_static_source",
        "is_synthetic": True,
        "h3_cell": cell_ids[0],
        "day_night": "D",
        "fire_type": "2",
    })

    # 3. Invalid row (is_valid == False, should be excluded)
    rows.append({
        "obs_id": "invalid_row",
        "source_id": "modis_c61",
        "sensor_family": "MODIS",
        "platform": "Terra",
        "processing_stream": "SP",
        "product_version": "6.1",
        "ingest_batch_id": "batch_1",
        "acq_date": date(2023, 1, 10),
        "local_date": date(2023, 1, 10),
        "lat": 28.0,
        "lon": 77.0,
        "is_valid": False,
        "qc_flags": "coordinate_out_of_range",
        "is_synthetic": True,
        "h3_cell": cell_ids[0],
        "day_night": "D",
        "fire_type": "0",
    })

    df = pd.DataFrame(rows)
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df


class TestCalibrationPreparation:
    """Test data filtering for calibration fitting."""

    def test_prepare_calibration_data_filters_correctly(self, sample_obs_clean: pd.DataFrame):
        prepared = prepare_calibration_data(sample_obs_clean)
        # Excludes NRT
        assert (prepared["processing_stream"] == "NRT").sum() == 0
        # Excludes possible_static_source
        assert prepared["qc_flags"].str.contains("possible_static_source").sum() == 0
        # Excludes is_valid == False
        assert (prepared["is_valid"] == False).sum() == 0
        # All remaining are SP and valid
        assert (prepared["processing_stream"] == "SP").all()
        assert (prepared["is_valid"] == True).all()

    def test_create_cell_day_matrix(self, sample_obs_clean: pd.DataFrame):
        prepared = prepare_calibration_data(sample_obs_clean)
        matrix = create_cell_day_matrix(prepared)

        assert not matrix.empty
        assert "h3_cell" in matrix.columns
        assert "date" in matrix.columns
        assert "terra_count" in matrix.columns
        assert "aqua_count" in matrix.columns
        assert "modis_count" in matrix.columns
        assert "snpp_count" in matrix.columns
        assert "noaa20_count" in matrix.columns
        assert "viirs_count" in matrix.columns
        assert "viirs_platform" in matrix.columns
        assert "is_provisional" in matrix.columns
        assert (matrix["modis_count"] == matrix["terra_count"] + matrix["aqua_count"]).all()


class TestTrainingUniverseAndHoldout:
    """Test Item 2: Training universe fills zeros across active cell-weeks and evaluates grain."""

    def test_build_training_universe_expands_active_cell_weeks(self, sample_obs_clean: pd.DataFrame):
        prepared = prepare_calibration_data(sample_obs_clean)
        matrix = create_cell_day_matrix(prepared)

        # Build cell-day training universe
        train_day = build_training_universe(matrix, grain="cell_day")
        assert not train_day.empty

        # Check zero-filling: cell-days in active weeks where MODIS=0 have VIIRS counts and vice-versa
        assert (train_day["modis_count"].isna()).sum() == 0
        assert (train_day["viirs_count"].isna()).sum() == 0

        # Build cell-week grain
        train_week = build_training_universe(matrix, grain="cell_week")
        assert not train_week.empty
        assert len(train_week) <= len(train_day)

    def test_fit_calibration_suite_evaluates_both_grains(self, sample_obs_clean: pd.DataFrame):
        suite = fit_calibration_suite(sample_obs_clean)
        assert suite.training_grain in ("cell_day", "cell_week")
        assert suite.mae_monthly_day >= 0.0
        assert suite.mae_monthly_week >= 0.0
        assert suite.modis_platform_rule == "aqua_preferred"


class TestSyntheticSmallFireRecovery:
    """Test Item 3: Plant VIIRS = 3 x MODIS plus extra small fires in cells where MODIS is 0.

    Shows that a model trained only on non-zero cell-days fails monthly recovery tolerance,
    while training on the complete universe succeeds.
    """

    def test_synthetic_small_fire_recovery(self):
        # 4 weeks of data
        dates = [date(2023, 5, 1) + timedelta(days=i) for i in range(28)]
        rows = []

        # Cell A: co-detected fires (MODIS=2, VIIRS = 3 x 2 = 6)
        for d in dates:
            rows.append({
                "h3_cell": "cell_A",
                "date": d,
                "day_night": "D",
                "terra_count": 1.0,
                "aqua_count": 1.0,
                "modis_count": 2.0,
                "snpp_count": 6.0,
                "noaa20_count": 0.0,
                "noaa21_count": 0.0,
                "viirs_count": 6.0,
            })

        # Cell B: small fires detected ONLY by VIIRS (MODIS=0, VIIRS=2)
        for d in dates[:14]:  # 14 days of small fires
            rows.append({
                "h3_cell": "cell_B",
                "date": d,
                "day_night": "D",
                "terra_count": 0.0,
                "aqua_count": 0.0,
                "modis_count": 0.0,
                "snpp_count": 2.0,
                "noaa20_count": 0.0,
                "noaa21_count": 0.0,
                "viirs_count": 2.0,
            })

        matrix = pd.DataFrame(rows)
        actual_monthly_viirs = matrix["viirs_count"].sum()  # 28*6 + 14*2 = 168 + 28 = 196
        total_modis = matrix["modis_count"].sum()            # 28*2 = 56

        # 1. Non-zero intersection model (MODIS > 0 and VIIRS > 0):
        # Only sees cell_A (ratio = 6 / 2 = 3.0)
        nonzero_overlap = matrix[(matrix["modis_count"] > 0) & (matrix["viirs_count"] > 0)]
        ratio_nonzero = nonzero_overlap["viirs_count"].sum() / nonzero_overlap["modis_count"].sum()
        assert ratio_nonzero == 3.0
        predicted_viirs_from_nonzero = ratio_nonzero * total_modis  # 3.0 * 56 = 168
        error_pct_nonzero = abs(predicted_viirs_from_nonzero - actual_monthly_viirs) / actual_monthly_viirs
        # Error is (196 - 168) / 196 = 14.3% -> FAILS 5% tolerance!
        assert error_pct_nonzero > 0.05, "Non-zero model should fail small-fire recovery tolerance"

        # 2. Training universe model (includes zero-MODIS days in active cell-weeks):
        train_univ = build_training_universe(matrix, grain="cell_day")
        denom = train_univ["modis_count"].sum()
        num = train_univ["viirs_count"].sum()
        ratio_universe = num / denom  # 196 / 56 = 3.5
        assert ratio_universe == 3.5
        predicted_viirs_from_universe = ratio_universe * total_modis  # 3.5 * 56 = 196
        error_pct_universe = abs(predicted_viirs_from_universe - actual_monthly_viirs) / actual_monthly_viirs
        # Error is 0% -> SUCCEEDS within tolerance!
        assert error_pct_universe <= 0.01


class TestTerraAquaRuleAndColumns:
    """Test Item 1, 4, 5: Aqua priority, observed intervals, and added columns."""

    def test_observed_intervals_have_no_poisson(self):
        # Observed count = 100: lower == upper == 100.0 (no Poisson noise)
        lower, upper = compute_observed_interval(100.0)
        assert lower == 100.0
        assert upper == 100.0

    def test_terra_aqua_priority_and_mart_columns(self, tmp_path: Path, sample_obs_clean: pd.DataFrame):
        suite = fit_calibration_suite(sample_obs_clean)
        from app.core.harmonization.temporal import aggregate_cell_day_activity

        cell_day_df = aggregate_cell_day_activity(sample_obs_clean[sample_obs_clean["is_valid"] == True])
        harm_df = apply_calibration_to_cell_days(cell_day_df, suite, data_dir=tmp_path, data_version="test.1.0")

        # Verify added columns
        required_cols = [
            "h3_cell", "acq_date", "day_night", "region_id",
            "harmonized_value", "harmonized_lower", "harmonized_upper",
            "modis_observed", "modis_terra_observed", "modis_aqua_observed",
            "viirs_observed", "viirs_platform", "platform_used",
            "interval_level", "method_id", "value_type",
            "is_provisional", "calibration_version", "data_version",
        ]
        for col in required_cols:
            assert col in harm_df.columns, f"Missing required column: {col}"

        # Day and night are kept separate
        assert set(harm_df["day_night"].unique()).issubset({"D", "N", "unknown"})

        # Observed records: lower == upper == observed
        observed = harm_df[harm_df["value_type"] == "observed"]
        assert (observed["harmonized_lower"] == observed["harmonized_value"]).all()
        assert (observed["harmonized_upper"] == observed["harmonized_value"]).all()

        # Calibration models mart contains modis_platform_rule and grain info
        con = sync_duckdb_views(data_dir=tmp_path)
        cal_models = con.execute("SELECT * FROM calibration_models").df()
        assert "modis_platform_rule" in cal_models.columns
        assert (cal_models["modis_platform_rule"] == "aqua_preferred").all()
        assert "training_grain" in cal_models.columns
        con.close()


class TestStaticMaskConditionAndMetrics:
    """Test Item 6: Static mask 50% condition and share metrics."""

    def test_static_mask_50_pct_condition(self):
        # Cell 1: 3 static detections out of 10 total archive detections (30% static) -> NOT masked
        rows_1 = [
            {"platform": "Terra", "lat": 20.0, "lon": 80.0, "acq_date": date(2022, 1, 1), "fire_type": "2"},
            {"platform": "Terra", "lat": 20.0, "lon": 80.0, "acq_date": date(2022, 1, 2), "fire_type": "2"},
            {"platform": "Terra", "lat": 20.0, "lon": 80.0, "acq_date": date(2022, 1, 3), "fire_type": "3"},
        ]
        for i in range(7):
            rows_1.append({"platform": "Terra", "lat": 20.0, "lon": 80.0, "acq_date": date(2022, 2, i + 1), "fire_type": "0"})

        # Cell 2: 4 static detections out of 5 total archive detections (80% static) -> MASKED
        rows_2 = [
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "acq_date": date(2022, 1, 1), "fire_type": "2"},
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "acq_date": date(2022, 1, 2), "fire_type": "2"},
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "acq_date": date(2022, 1, 3), "fire_type": "3"},
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "acq_date": date(2022, 1, 4), "fire_type": "2"},
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "acq_date": date(2022, 2, 1), "fire_type": "0"},
        ]

        df = pd.DataFrame(rows_1 + rows_2)
        mask = build_static_source_mask(df, h3_resolution=8, min_distinct_days=3, min_static_pct=50.0)

        # Only Cell 2 should qualify
        import h3
        cell_1_h3 = h3.latlng_to_cell(20.0, 80.0, 8)
        cell_2_h3 = h3.latlng_to_cell(25.0, 85.0, 8)
        assert ("Terra", cell_1_h3) not in mask
        assert ("Terra", cell_2_h3) in mask

    def test_compute_static_mask_metrics(self):
        import h3
        cell_h3 = h3.latlng_to_cell(25.0, 85.0, 8)
        mask = {("Terra", cell_h3)}

        df = pd.DataFrame([
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "processing_stream": "NRT", "fire_type": "0"},
            {"platform": "Terra", "lat": 25.0, "lon": 85.0, "processing_stream": "SP", "fire_type": "2"},
            {"platform": "Terra", "lat": 20.0, "lon": 80.0, "processing_stream": "SP", "fire_type": "0"},
        ])

        metrics = compute_static_mask_metrics(df, mask, h3_resolution=8)
        assert metrics["total_nrt"] == 1
        assert metrics["nrt_flagged"] == 1
        assert metrics["nrt_flagged_share"] == 1.0
        assert metrics["total_archive_type0"] == 1
        assert metrics["archive_type0_in_mask"] == 0
        assert metrics["archive_type0_share"] == 0.0
        assert metrics["total_archive_static"] == 1
        assert metrics["archive_static_in_mask"] == 1
        assert metrics["archive_static_share"] == 1.0


class TestStorageOptimizations:
    """Test Item 8: extras dropped, obs_id 16-char hash, and zstd compression in stage_clean."""

    def test_stage_clean_storage_optimizations(self, tmp_path: Path):
        # Create staging canonical observation file with extras column and long obs_id
        staging_all = tmp_path / "staging" / "obs_all"
        staging_all.mkdir(parents=True, exist_ok=True)

        long_id = "firms_modis_c61_india_2023_very_long_identifier_0123456789"
        row = {
            "obs_id": long_id,
            "source_id": "modis_c61",
            "sensor_family": "MODIS",
            "platform": "Terra",
            "processing_stream": "SP",
            "product_version": "6.1",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 1, 1),
            "lat": 25.0,
            "lon": 80.0,
            "is_valid": True,
            "qc_flags": "",
            "is_synthetic": True,
            "confidence_raw": "80",
            "confidence_class": "nominal",
            "extras": '{"unmapped": "sample"}',
        }
        for c in CANONICAL_COLUMNS:
            if c not in row:
                row[c] = None
        obs_df = pd.DataFrame([row])
        obs_df.to_parquet(staging_all / "modis_c61_sample.parquet", index=False)

        res = stage_clean(data_dir=tmp_path)
        assert res["rows_out"] == 1

        obs_clean_file = tmp_path / "staging" / "obs_clean.parquet"
        assert obs_clean_file.exists()

        clean_df = pd.read_parquet(obs_clean_file)
        # 1. Extras dropped
        assert "extras" not in clean_df.columns
        # 2. Obs_id shortened to 16-char SHA-256 hash
        assert len(clean_df["obs_id"].iloc[0]) == 16
        expected_hash = hashlib.sha256(long_id.encode("utf-8")).hexdigest()[:16]
        assert clean_df["obs_id"].iloc[0] == expected_hash


class TestCalibrationFreezeRules:
    """Test Task 7f: Single VIIRS reference, uncertainty intervals, and deterministic reproducibility."""

    def test_single_viirs_reference_rule_never_sums_platforms(self):
        """Item 1: Exactly one VIIRS reference series, never the sum of two VIIRS platforms."""
        # Day 1: Both S-NPP and NOAA-20 present. Reference must be S-NPP alone.
        # Day 2: S-NPP absent (outage), NOAA-20 present. Reference must be NOAA-20.
        records = [
            # Day 1
            {"h3_cell": "86618925fffffff", "date": date(2022, 5, 1), "day_night": "D", "platform": "S-NPP", "obs_id": "1"},
            {"h3_cell": "86618925fffffff", "date": date(2022, 5, 1), "day_night": "D", "platform": "S-NPP", "obs_id": "2"},
            {"h3_cell": "86618925fffffff", "date": date(2022, 5, 1), "day_night": "D", "platform": "NOAA-20", "obs_id": "3"},
            {"h3_cell": "86618925fffffff", "date": date(2022, 5, 1), "day_night": "D", "platform": "NOAA-20", "obs_id": "4"},
            {"h3_cell": "86618925fffffff", "date": date(2022, 5, 1), "day_night": "D", "platform": "NOAA-20", "obs_id": "5"},
            # Day 2: S-NPP outage
            {"h3_cell": "86618925fffffff", "date": date(2022, 8, 1), "day_night": "D", "platform": "NOAA-20", "obs_id": "6"},
            {"h3_cell": "86618925fffffff", "date": date(2022, 8, 1), "day_night": "D", "platform": "NOAA-20", "obs_id": "7"},
        ]
        df = pd.DataFrame(records)
        matrix = create_cell_day_matrix(df)

        # Day 1 checks
        d1 = matrix[matrix["date"] == date(2022, 5, 1)].iloc[0]
        assert d1["snpp_count"] == 2.0
        assert d1["noaa20_count"] == 3.0
        # CRUCIAL: Must NOT be 2 + 3 = 5! Must be 2 (S-NPP alone)
        assert d1["viirs_count"] == 2.0
        assert d1["viirs_platform"] == "S-NPP"
        assert "+" not in d1["viirs_platform"]

        # Day 2 checks
        d2 = matrix[matrix["date"] == date(2022, 8, 1)].iloc[0]
        assert d2["snpp_count"] == 0.0
        assert d2["noaa20_count"] == 2.0
        assert d2["viirs_count"] == 2.0
        assert d2["viirs_platform"] == "NOAA-20"
        assert "+" not in d2["viirs_platform"]

    def test_interval_for_size_classes_and_reliability(self):
        """Item 3: interval_for returns lower/upper bounds with bridge term and reliability label,
        or (None, None, 'insufficient') when expected_count < 10."""
        from app.core.harmonization.uncertainty import interval_for

        # Very small: [0, 10) returns (None, None, 'insufficient')
        l_vs, u_vs, rel_vs = interval_for(5.0)
        assert l_vs is None
        assert u_vs is None
        assert rel_vs == "insufficient"

        # Also for 0.0 and negative
        l_0, u_0, rel_0 = interval_for(0.0)
        assert l_0 is None and u_0 is None and rel_0 == "insufficient"

        # Small: [10, 50)
        l_s, u_s, rel_s = interval_for(25.0)
        assert l_s is not None and u_s is not None
        assert rel_s in ("low", "medium")

        # Macro: >= 5000 (country-wide)
        l_macro, u_macro, rel_macro = interval_for(15000.0)
        assert l_macro is not None and u_macro is not None
        assert rel_macro in ("low", "medium", "high")

    def test_static_masked_excluded_from_aggregation(self):
        """Task 7g Item 2: static NRT rows are excluded from the current month (Nov 2026)."""
        from app.core.harmonization.temporal import aggregate_cell_day_activity

        # Current month fixture (Nov 2026)
        df = pd.DataFrame({
            "obs_id": ["nrt_nov_veg", "nrt_nov_static", "nrt_nov_veg2"],
            "source_id": ["viirs_noaa20", "viirs_noaa20", "viirs_noaa20"],
            "sensor_family": ["VIIRS", "VIIRS", "VIIRS"],
            "platform": ["NOAA-20", "NOAA-20", "NOAA-20"],
            "h3_cell": ["883c120ea1fffff", "883c120ea1fffff", "883c120ea1fffff"],
            "acq_date": ["2026-11-05", "2026-11-05", "2026-11-05"],
            "local_date": ["2026-11-05", "2026-11-05", "2026-11-05"],
            "day_night": ["D", "D", "D"],
            "confidence_class": ["high", "nominal", "high"],
            "frp_mw": [15.0, 50.0, 25.0],
            "is_valid": [True, True, True],
            "processing_stream": ["NRT", "NRT", "NRT"],
            "static_masked": [False, True, False],
        })

        agg = aggregate_cell_day_activity(df)
        assert len(agg) == 1
        # The static NRT detection (nrt_nov_static with 50.0 MW) is excluded
        assert agg["n_detections"].iloc[0] == 2
        assert agg["frp_sum_mw"].iloc[0] == 40.0

    def test_viirs_reference_order_november_2026(self):
        """Task 7g Item 5: Reference for 3-9 Nov 2026 uses NOAA-20 or NOAA-21 after S-NPP end date."""
        from app.core.harmonization.calibration import create_cell_day_matrix

        # Fixture spanning Oct 31 to Nov 09, 2026 where S-NPP ends on 2026-10-31
        rows = [
            {"h3_cell": "86618e38fffffff", "acq_date": "2026-10-31", "platform": "S-NPP", "day_night": "D", "obs_id": "s1"},
            {"h3_cell": "86618e38fffffff", "acq_date": "2026-10-31", "platform": "NOAA-20", "day_night": "D", "obs_id": "n1"},
            {"h3_cell": "86618e38fffffff", "acq_date": "2026-11-03", "platform": "NOAA-20", "day_night": "D", "obs_id": "n2"},
            {"h3_cell": "86618e38fffffff", "acq_date": "2026-11-09", "platform": "NOAA-21", "day_night": "D", "obs_id": "n3"},
        ]
        test_df = pd.DataFrame(rows)
        matrix = create_cell_day_matrix(test_df)

        oct31 = matrix[matrix["date"] == date(2026, 10, 31)].iloc[0]
        assert oct31["viirs_platform"] == "S-NPP"

        nov03 = matrix[matrix["date"] == date(2026, 11, 3)].iloc[0]
        assert nov03["viirs_platform"] == "NOAA-20"
        assert nov03["viirs_count"] == 1.0

        nov09 = matrix[matrix["date"] == date(2026, 11, 9)].iloc[0]
        assert nov09["viirs_platform"] in ("NOAA-20", "NOAA-21")
        assert nov09["viirs_count"] == 1.0

    def test_series_parameter_analytics_layer(self):
        """Task 7g Item 3: series parameter in get_harmonized."""
        from app.utils.data_repository import DataRepository
        from pathlib import Path

        repo = DataRepository(data_dir=Path("data/slice_2019_2022/marts"), mode="fixture")
        # Default harmonized
        h_df = repo.get_harmonized()
        assert not h_df.empty

        # VIIRS native
        v_df = repo.get_harmonized(series="viirs_native")
        if not v_df.empty:
            assert (v_df["value_type"] == "observed").all()
            assert (v_df["method_id"] == "viirs_native").all()

        # MODIS native
        m_df = repo.get_harmonized(series="modis_native")
        if not m_df.empty:
            assert (m_df["value_type"] == "observed").all()
            assert (m_df["method_id"] == "modis_native").all()

    def test_bootstrap_seeding_is_deterministic(self):
        """Item 4: Reruns with config random_seed produce byte-identical numbers."""
        from app.core.harmonization.uncertainty import compute_block_bootstrap_ratios

        # Synthetic data
        dates = pd.date_range("2022-01-01", periods=60)
        rng = np.random.default_rng(123)
        modis = rng.poisson(10, size=60)
        viirs = rng.poisson(30, size=60)
        df = pd.DataFrame({"date": dates, "modis_count": modis, "viirs_count": viirs})

        res1 = compute_block_bootstrap_ratios(df, random_seed=42)
        res2 = compute_block_bootstrap_ratios(df, random_seed=42)

        assert res1["mean_ratio"] == res2["mean_ratio"]
        assert res1["lower_ratio"] == res2["lower_ratio"]
        assert res1["upper_ratio"] == res2["upper_ratio"]
        assert res1["rel_lower_err"] == res2["rel_lower_err"]
        assert res1["rel_upper_err"] == res2["rel_upper_err"]

    def test_noaa20_static_nrt_rows_excluded_november_2026(self):
        """Task 8b Item 7: NOAA-20 static NRT rows for 3-9 Nov 2026 are excluded the same way as S-NPP rows."""
        from app.core.harmonization.temporal import aggregate_cell_day_activity

        # Test both S-NPP (late Oct / early Nov) and NOAA-20 (3-9 Nov 2026) static NRT rows
        df = pd.DataFrame({
            "obs_id": ["snpp_static", "snpp_veg", "noaa20_static_flag", "noaa20_static_qc", "noaa20_veg"],
            "source_id": ["viirs_snpp", "viirs_snpp", "viirs_noaa20", "viirs_noaa20", "viirs_noaa20"],
            "sensor_family": ["VIIRS", "VIIRS", "VIIRS", "VIIRS", "VIIRS"],
            "platform": ["S-NPP", "S-NPP", "NOAA-20", "NOAA-20", "NOAA-20"],
            "h3_cell": ["883c120ea1fffff", "883c120ea1fffff", "883c120ea1fffff", "883c120ea1fffff", "883c120ea1fffff"],
            "acq_date": ["2026-11-01", "2026-11-01", "2026-11-05", "2026-11-05", "2026-11-05"],
            "local_date": ["2026-11-01", "2026-11-01", "2026-11-05", "2026-11-05", "2026-11-05"],
            "day_night": ["D", "D", "D", "D", "D"],
            "confidence_class": ["high", "high", "high", "high", "high"],
            "frp_mw": [100.0, 20.0, 80.0, 60.0, 30.0],
            "is_valid": [True, True, True, True, True],
            "processing_stream": ["NRT", "NRT", "NRT", "NRT", "NRT"],
            "static_masked": [True, False, True, False, False],
            "qc_flags": ["possible_static_source", "", "possible_static_source", "possible_static_source", ""],
        })

        agg = aggregate_cell_day_activity(df)
        assert len(agg) == 2  # 1 row for Nov 1 (S-NPP), 1 row for Nov 5 (NOAA-20)

        # Nov 1 (S-NPP): static detection (100 MW) excluded, only veg (20 MW) kept
        snpp_agg = agg[pd.to_datetime(agg["date"]).dt.date == date(2026, 11, 1)].iloc[0]
        assert snpp_agg["n_detections"] == 1
        assert snpp_agg["frp_sum_mw"] == 20.0

        # Nov 5 (NOAA-20): both static detections (80 MW flagged via static_masked, 60 MW flagged via qc_flags) excluded
        # Only veg detection (30 MW) kept
        noaa20_agg = agg[pd.to_datetime(agg["date"]).dt.date == date(2026, 11, 5)].iloc[0]
        assert noaa20_agg["n_detections"] == 1
        assert noaa20_agg["frp_sum_mw"] == 30.0

    def test_viirs_era_double_count_elimination(self, tmp_path: Path):
        """Task 8b Item 4 & 5: In VIIRS era, viirs_platform 'none' rows have harmonized_value=0.0."""
        from app.core.harmonization.calibration import fit_calibration_suite, apply_calibration_to_cell_days

        # Create observations with both pre-VIIRS (2010) and VIIRS-era (2022) dates
        obs = pd.DataFrame({
            "obs_id": [f"obs_{i}" for i in range(8)],
            "source_id": ["modis_c61"] * 4 + ["viirs_snpp"] * 2 + ["modis_c61"] * 2,
            "sensor_family": ["MODIS"] * 4 + ["VIIRS"] * 2 + ["MODIS"] * 2,
            "platform": ["Aqua", "Terra", "Aqua", "Terra", "S-NPP", "S-NPP", "Aqua", "Terra"],
            "h3_cell": ["86618e38fffffff"] * 8,
            "acq_date": [
                "2010-05-01", "2010-05-01",  # pre-VIIRS
                "2010-05-02", "2010-05-02",  # pre-VIIRS
                "2022-05-01", "2022-05-01",  # VIIRS-era cell with VIIRS detection
                "2022-05-02", "2022-05-02",  # VIIRS-era cell with MODIS ONLY (viirs_obs = 0)
            ],
            "local_date": [
                "2010-05-01", "2010-05-01",
                "2010-05-02", "2010-05-02",
                "2022-05-01", "2022-05-01",
                "2022-05-02", "2022-05-02",
            ],
            "day_night": ["D"] * 8,
            "confidence_class": ["high"] * 8,
            "frp_mw": [20.0] * 8,
            "is_valid": [True] * 8,
            "processing_stream": ["SP"] * 8,
        })

        from app.core.harmonization.temporal import aggregate_cell_day_activity
        cell_day = aggregate_cell_day_activity(obs)
        suite = fit_calibration_suite(obs)
        harm = apply_calibration_to_cell_days(cell_day, suite, data_dir=tmp_path)

        # 1. Pre-VIIRS row (2010-05-01): estimated from MODIS, value_type is 'estimated, extrapolated'
        pre_row = harm[pd.to_datetime(harm["acq_date"]).dt.date == date(2010, 5, 1)].iloc[0]
        assert pre_row["value_type"] == "estimated, extrapolated"
        assert pre_row["harmonized_value"] > 0.0

        # 2. VIIRS era cell with VIIRS detection (2022-05-01): equals VIIRS count
        viirs_row = harm[pd.to_datetime(harm["acq_date"]).dt.date == date(2022, 5, 1)].iloc[0]
        assert viirs_row["value_type"] == "observed"
        assert viirs_row["harmonized_value"] == viirs_row["viirs_observed"]

        # 3. VIIRS era cell with MODIS ONLY (2022-05-02): NO DOUBLE COUNT.
        # VIIRS reference is 0.0, harmonized_value is 0.0, NOT MODIS-converted.
        zero_row = harm[pd.to_datetime(harm["acq_date"]).dt.date == date(2022, 5, 2)].iloc[0]
        assert zero_row["viirs_observed"] == 0.0
        assert zero_row["harmonized_value"] == 0.0
        assert zero_row["harmonized_lower"] == 0.0
        assert zero_row["harmonized_upper"] == 0.0

    def test_harmonized_cell_day_mart_has_zero_spurious_viirs_era_rows(self):
        """Verify Task 11 Item 1: mart has exactly zero VIIRS-era rows with viirs_platform 'none' and harmonized_value > 0."""
        from app.settings import settings
        import duckdb
        harm_path = settings.data_dir / "marts" / "harmonized_cell_day.parquet"
        if not harm_path.exists():
            pytest.skip("Production mart harmonized_cell_day.parquet not present in test environment")

        con = duckdb.connect()
        query = f"""
            SELECT COUNT(*)
            FROM read_parquet('{harm_path.as_posix()}')
            WHERE acq_date >= '2012-01-20'
              AND viirs_platform = 'none'
              AND harmonized_value > 0
        """
        spurious_count = con.execute(query).fetchone()[0]
        assert spurious_count == 0, f"Expected 0 spurious VIIRS-era rows, found {spurious_count}"



