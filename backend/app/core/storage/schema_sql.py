"""DuckDB schema and view definitions for TerraFlare data lake."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from app.shared.canonical import CANONICAL_COLUMNS


def get_view_definitions(data_dir: Path) -> dict[str, str]:
    """Return SQL DDL for views over parquet files in the data lake.

    Forward slashes are used for cross-platform DuckDB compatibility.
    """
    clean_dir = data_dir.resolve().as_posix()

    obs_clean_path = f"{clean_dir}/staging/obs_clean.parquet"
    obs_all_path = f"{clean_dir}/staging/obs_all/*.parquet"
    cell_day_path = f"{clean_dir}/marts/cell_day_activity.parquet"
    harmonized_path = f"{clean_dir}/marts/harmonized_cell_day.parquet"
    monthly_path = f"{clean_dir}/marts/monthly_activity.parquet"
    ingest_log_path = f"{clean_dir}/staging/ingest_log.parquet"
    cleaning_report_path = f"{clean_dir}/staging/cleaning_report.parquet"
    calibration_models_path = f"{clean_dir}/marts/calibration_models.parquet"

    views = {}

    # 1. obs_clean (point-level canonical observations)
    # Prefer obs_clean.parquet if it exists; otherwise view over obs_all where is_valid
    p_clean = data_dir / "staging" / "obs_clean.parquet"
    p_all = data_dir / "staging" / "obs_all"
    if p_clean.exists():
        views["obs_clean"] = f"CREATE OR REPLACE VIEW obs_clean AS SELECT * FROM read_parquet('{obs_clean_path}');"
    elif p_all.exists() and any(p_all.glob("*.parquet")):
        views["obs_clean"] = f"CREATE OR REPLACE VIEW obs_clean AS SELECT * FROM read_parquet('{obs_all_path}') WHERE is_valid = true;"
    else:
        views["obs_clean"] = "CREATE OR REPLACE VIEW obs_clean AS SELECT * FROM empty_obs_clean;"

    # 2. cell_day_activity
    if (data_dir / "marts" / "cell_day_activity.parquet").exists():
        views["cell_day_activity"] = f"CREATE OR REPLACE VIEW cell_day_activity AS SELECT * FROM read_parquet('{cell_day_path}');"
    else:
        views["cell_day_activity"] = "CREATE OR REPLACE VIEW cell_day_activity AS SELECT * FROM empty_cell_day;"

    # 3. harmonized_cell_day
    if (data_dir / "marts" / "harmonized_cell_day.parquet").exists():
        views["harmonized_cell_day"] = f"CREATE OR REPLACE VIEW harmonized_cell_day AS SELECT * FROM read_parquet('{harmonized_path}');"
    else:
        views["harmonized_cell_day"] = "CREATE OR REPLACE VIEW harmonized_cell_day AS SELECT * FROM empty_harmonized;"

    # 4. monthly_activity
    if (data_dir / "marts" / "monthly_activity.parquet").exists():
        views["monthly_activity"] = f"CREATE OR REPLACE VIEW monthly_activity AS SELECT * FROM read_parquet('{monthly_path}');"
    else:
        views["monthly_activity"] = "CREATE OR REPLACE VIEW monthly_activity AS SELECT * FROM empty_monthly;"

    # 5. ingest_log
    if (data_dir / "staging" / "ingest_log.parquet").exists():
        views["ingest_log"] = f"CREATE OR REPLACE VIEW ingest_log AS SELECT * FROM read_parquet('{ingest_log_path}');"
    else:
        views["ingest_log"] = "CREATE OR REPLACE VIEW ingest_log AS SELECT * FROM empty_ingest_log;"

    # 6. cleaning_report
    if (data_dir / "staging" / "cleaning_report.parquet").exists():
        views["cleaning_report"] = f"CREATE OR REPLACE VIEW cleaning_report AS SELECT * FROM read_parquet('{cleaning_report_path}');"
    else:
        views["cleaning_report"] = "CREATE OR REPLACE VIEW cleaning_report AS SELECT * FROM empty_cleaning_report;"

    # 7. calibration_models
    if (data_dir / "marts" / "calibration_models.parquet").exists():
        views["calibration_models"] = f"CREATE OR REPLACE VIEW calibration_models AS SELECT * FROM read_parquet('{calibration_models_path}');"
    else:
        views["calibration_models"] = "CREATE OR REPLACE VIEW calibration_models AS SELECT * FROM empty_calibration_models;"

    return views


def initialize_empty_fallback_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create empty tables so views can always be queried even before data is generated."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS empty_obs_clean (
            obs_id VARCHAR, source_id VARCHAR, sensor_family VARCHAR, platform VARCHAR,
            processing_stream VARCHAR, product_version VARCHAR, ingest_batch_id VARCHAR,
            acq_date DATE, lat DOUBLE, lon DOUBLE, is_valid BOOLEAN, qc_flags VARCHAR,
            is_synthetic BOOLEAN, acq_datetime_utc TIMESTAMP, local_date DATE,
            h3_cell VARCHAR, confidence_raw VARCHAR, confidence_class VARCHAR,
            frp_mw DOUBLE, day_night VARCHAR, fire_type VARCHAR, satellite_raw VARCHAR,
            instrument_raw VARCHAR, extras VARCHAR
        );
        CREATE TABLE IF NOT EXISTS empty_cell_day (
            source_id VARCHAR, sensor_family VARCHAR, platform VARCHAR, h3_cell VARCHAR,
            date DATE, day_night VARCHAR, n_detections BIGINT, n_high_conf BIGINT,
            frp_sum_mw DOUBLE, frp_max_mw DOUBLE
        );
        CREATE TABLE IF NOT EXISTS empty_harmonized (
            h3_cell VARCHAR, acq_date DATE, day_night VARCHAR, region_id VARCHAR,
            harmonized_value DOUBLE, harmonized_lower DOUBLE, harmonized_upper DOUBLE,
            modis_observed DOUBLE, modis_terra_observed DOUBLE, modis_aqua_observed DOUBLE,
            viirs_observed DOUBLE, viirs_platform VARCHAR, platform_used VARCHAR,
            interval_level DOUBLE, method_id VARCHAR, value_type VARCHAR,
            is_provisional BOOLEAN, calibration_version VARCHAR, data_version VARCHAR
        );
        CREATE TABLE IF NOT EXISTS empty_monthly (
            region_id VARCHAR, year_month VARCHAR, value_type VARCHAR,
            sensor_family VARCHAR, value DOUBLE, lower DOUBLE, upper DOUBLE,
            data_version VARCHAR
        );
        CREATE TABLE IF NOT EXISTS empty_ingest_log (
            source_id VARCHAR, file_name VARCHAR, sha256 VARCHAR,
            rows_in BIGINT, ingested_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS empty_cleaning_report (
            rule_id VARCHAR, source_id VARCHAR, rows_flagged BIGINT, rows_dropped BIGINT
        );
        CREATE TABLE IF NOT EXISTS empty_calibration_models (
            platform VARCHAR, target_sensor VARCHAR, method_id VARCHAR,
            global_ratio DOUBLE, strata_ratios_json VARCHAR, regression_params_json VARCHAR,
            uncertainty_json VARCHAR, n_cell_days_used BIGINT, n_months_evaluated BIGINT,
            mae_monthly DOUBLE, rmse_monthly DOUBLE, bias_monthly DOUBLE, rel_mae_monthly DOUBLE,
            bridge_min_date VARCHAR, bridge_max_date VARCHAR, bridge_ratio DOUBLE,
            modis_platform_rule VARCHAR, training_grain VARCHAR, mae_monthly_day DOUBLE,
            mae_monthly_week DOUBLE, calibration_version VARCHAR, fitted_at VARCHAR
        );
    """)


def create_views(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    """Create or refresh all views in DuckDB."""
    initialize_empty_fallback_tables(con)
    views = get_view_definitions(data_dir)
    for sql in views.values():
        con.execute(sql)

