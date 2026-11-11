"""Tests for cleaning rules, normalisation, and cleaning report generation (Task 4)."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from app.core.cleaning.normalize import (
    compute_solar_local_date,
    normalize_canonical_dataframe,
    normalize_confidence_modis,
    normalize_confidence_viirs,
)
from app.core.cleaning.report import (
    build_cleaning_report,
    clean_observations,
    format_cleaning_report,
    print_cleaning_report,
)
from app.core.cleaning.rules import (
    apply_cleaning_rules,
    check_coordinate_range,
    check_duplicate_obs_id,
    check_missing_date,
    check_negative_frp,
    filter_confidence,
    filter_fire_type,
)
from app.core.ingestion.adapters.firms_csv import FirmsCSVAdapter
from app.shared.canonical import CANONICAL_COLUMNS, empty_canonical_frame

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _make_row(**kwargs) -> dict:
    base = {
        "obs_id": "obs_001",
        "source_id": "modis_c61",
        "sensor_family": "MODIS",
        "platform": "Terra",
        "processing_stream": "SP",
        "product_version": "Collection 6.1",
        "ingest_batch_id": "b1",
        "acq_date": date(2023, 6, 15),
        "acq_datetime_utc": datetime(2023, 6, 15, 12, 0, 0),
        "lat": 15.5,
        "lon": 73.8,
        "is_valid": True,
        "qc_flags": "[]",
        "is_synthetic": False,
        "confidence_raw": "65",
        "confidence_class": "nominal",
        "frp_mw": 15.0,
        "day_night": "D",
        "fire_type": "0",
        "satellite_raw": "Terra",
        "instrument_raw": "MODIS",
        "extras": "{}",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# 1. Coordinate range rule tests
# ---------------------------------------------------------------------------

def test_coordinate_range_valid_and_invalid():
    df = pd.DataFrame([
        _make_row(obs_id="valid", lat=15.5, lon=73.8),
        _make_row(obs_id="lat_high", lat=91.0, lon=73.8),
        _make_row(obs_id="lat_low", lat=-90.5, lon=73.8),
        _make_row(obs_id="lon_high", lat=15.5, lon=181.0),
        _make_row(obs_id="lon_low", lat=15.5, lon=-185.0),
        _make_row(obs_id="lat_nan", lat=float("nan"), lon=73.8),
    ])

    out, count = check_coordinate_range(df)
    assert count == 5
    assert bool(out.loc[0, "is_valid"]) is True
    assert out.loc[0, "qc_flags"] == "[]"

    for i in range(1, 6):
        assert bool(out.loc[i, "is_valid"]) is False
        flags = json.loads(out.loc[i, "qc_flags"])
        assert "invalid_coordinates" in flags


# ---------------------------------------------------------------------------
# 2. Missing date rule tests
# ---------------------------------------------------------------------------

def test_missing_date_rule():
    df = pd.DataFrame([
        _make_row(obs_id="has_date", acq_date=date(2023, 6, 15)),
        _make_row(obs_id="missing_date", acq_date=None),
        _make_row(obs_id="nat_date", acq_date=pd.NaT),
    ])

    out, count = check_missing_date(df)
    assert count == 2
    assert bool(out.loc[0, "is_valid"]) is True
    assert bool(out.loc[1, "is_valid"]) is False
    assert bool(out.loc[2, "is_valid"]) is False
    assert "missing_date" in json.loads(out.loc[1, "qc_flags"])


# ---------------------------------------------------------------------------
# 3. Duplicate obs_id rule tests
# ---------------------------------------------------------------------------

def test_duplicate_obs_id_rule():
    df = pd.DataFrame([
        _make_row(obs_id="id_1"),
        _make_row(obs_id="id_2"),
        _make_row(obs_id="id_1"),  # duplicate
        _make_row(obs_id="id_1"),  # triplicate
    ])

    out, count = check_duplicate_obs_id(df)
    assert count == 2
    assert bool(out.loc[0, "is_valid"]) is True
    assert bool(out.loc[1, "is_valid"]) is True
    assert bool(out.loc[2, "is_valid"]) is False
    assert bool(out.loc[3, "is_valid"]) is False
    assert "duplicate_obs_id" in json.loads(out.loc[2, "qc_flags"])


# ---------------------------------------------------------------------------
# 4. Fire type filter tests
# ---------------------------------------------------------------------------

def test_fire_type_filter():
    df = pd.DataFrame([
        _make_row(obs_id="veg", fire_type="0"),
        _make_row(obs_id="static_source", fire_type="2"),
        _make_row(obs_id="offshore", fire_type="3"),
        _make_row(obs_id="volcano", fire_type="1"),
        _make_row(obs_id="no_type_field", fire_type=None),
        _make_row(obs_id="empty_type", fire_type=""),
    ])

    out, count = filter_fire_type(df)
    # Types 2, 3, 1 are non-vegetation fires and must be flagged
    assert count == 3
    assert bool(out.loc[0, "is_valid"]) is True
    assert bool(out.loc[1, "is_valid"]) is False
    assert bool(out.loc[2, "is_valid"]) is False
    assert bool(out.loc[3, "is_valid"]) is False
    assert bool(out.loc[4, "is_valid"]) is True  # missing fire_type not flagged
    assert bool(out.loc[5, "is_valid"]) is True

    assert "non_vegetation_fire" in json.loads(out.loc[1, "qc_flags"])


def test_fire_type_filter_configurable():
    df = pd.DataFrame([
        _make_row(obs_id="r1", fire_type="0"),
        _make_row(obs_id="r2", fire_type="2"),
    ])
    # Allowing type "2" explicitly
    out, count = filter_fire_type(df, allowed_types={"0", "2"})
    assert count == 0
    assert out["is_valid"].all()


# ---------------------------------------------------------------------------
# 5. Confidence filter tests
# ---------------------------------------------------------------------------

def test_confidence_filter_rule():
    df = pd.DataFrame([
        _make_row(obs_id="high", confidence_class="high"),
        _make_row(obs_id="nominal", confidence_class="nominal"),
        _make_row(obs_id="low", confidence_class="low"),
        _make_row(obs_id="unknown", confidence_class="unknown"),
    ])

    # Default min_confidence is nominal -> low and unknown are flagged
    out, count = filter_confidence(df, min_confidence_class="nominal")
    assert count == 2
    assert bool(out.loc[0, "is_valid"]) is True
    assert bool(out.loc[1, "is_valid"]) is True
    assert bool(out.loc[2, "is_valid"]) is False
    assert bool(out.loc[3, "is_valid"]) is False
    assert "below_min_confidence" in json.loads(out.loc[2, "qc_flags"])


# ---------------------------------------------------------------------------
# 6. Negative FRP rule tests
# ---------------------------------------------------------------------------

def test_negative_frp_rule():
    df = pd.DataFrame([
        _make_row(obs_id="pos_frp", frp_mw=12.5),
        _make_row(obs_id="zero_frp", frp_mw=0.0),
        _make_row(obs_id="neg_frp", frp_mw=-1.5),
        _make_row(obs_id="none_frp", frp_mw=None),
    ])

    out, count = check_negative_frp(df)
    assert count == 1
    assert bool(out.loc[0, "is_valid"]) is True
    assert bool(out.loc[1, "is_valid"]) is True
    assert bool(out.loc[2, "is_valid"]) is False
    assert bool(out.loc[3, "is_valid"]) is True
    assert "negative_frp" in json.loads(out.loc[2, "qc_flags"])


# ---------------------------------------------------------------------------
# 7. MODIS confidence boundaries (29, 30, 80, 81)
# ---------------------------------------------------------------------------

def test_modis_confidence_exact_boundaries():
    assert normalize_confidence_modis(0) == "low"
    assert normalize_confidence_modis(29) == "low"
    assert normalize_confidence_modis("29") == "low"
    assert normalize_confidence_modis(30) == "nominal"
    assert normalize_confidence_modis("30") == "nominal"
    assert normalize_confidence_modis(50) == "nominal"
    assert normalize_confidence_modis(80) == "nominal"
    assert normalize_confidence_modis("80") == "nominal"
    assert normalize_confidence_modis(81) == "high"
    assert normalize_confidence_modis("81") == "high"
    assert normalize_confidence_modis(100) == "high"
    assert normalize_confidence_modis(None) == "unknown"
    assert normalize_confidence_modis("bad_str") == "unknown"


# ---------------------------------------------------------------------------
# 8. VIIRS confidence mapping tests
# ---------------------------------------------------------------------------

def test_viirs_confidence_mapping():
    assert normalize_confidence_viirs("l") == "low"
    assert normalize_confidence_viirs("L") == "low"
    assert normalize_confidence_viirs("low") == "low"
    assert normalize_confidence_viirs("n") == "nominal"
    assert normalize_confidence_viirs("N") == "nominal"
    assert normalize_confidence_viirs("nominal") == "nominal"
    assert normalize_confidence_viirs("h") == "high"
    assert normalize_confidence_viirs("H") == "high"
    assert normalize_confidence_viirs("high") == "high"
    assert normalize_confidence_viirs("unknown") == "unknown"
    assert normalize_confidence_viirs(None) == "unknown"


# ---------------------------------------------------------------------------
# 9. Local solar date day-boundary tests
# ---------------------------------------------------------------------------

def test_solar_local_date_day_boundary_forward():
    # UTC: 2023-06-15 at 22:30:00 (late evening)
    # Longitude: 80.0°E (India region)
    # Offset: +80 / 15 = +5.3333 hours (+5 hours 20 minutes)
    # Local solar time = 2023-06-16 03:50:00 -> Date crosses forward into 2023-06-16!
    utc_dt = datetime(2023, 6, 15, 22, 30, 0)
    lon = 80.0
    loc_date = compute_solar_local_date(utc_dt, lon)

    assert utc_dt.date() == date(2023, 6, 15)
    assert loc_date == date(2023, 6, 16)


def test_solar_local_date_day_boundary_backward():
    # UTC: 2023-06-15 at 01:00:00 (early morning)
    # Longitude: -60.0°W (Americas)
    # Offset: -60 / 15 = -4.0 hours
    # Local solar time = 2023-06-14 21:00:00 -> Date crosses backward into 2023-06-14!
    utc_dt = datetime(2023, 6, 15, 1, 0, 0)
    lon = -60.0
    loc_date = compute_solar_local_date(utc_dt, lon)

    assert utc_dt.date() == date(2023, 6, 15)
    assert loc_date == date(2023, 6, 14)


def test_solar_local_date_same_day():
    # UTC: 2023-06-15 at 12:00:00 (noon)
    # Longitude: 75.0°E -> +5.0 hours -> 17:00:00 same date
    utc_dt = datetime(2023, 6, 15, 12, 0, 0)
    lon = 75.0
    loc_date = compute_solar_local_date(utc_dt, lon)
    assert loc_date == date(2023, 6, 15)


# ---------------------------------------------------------------------------
# 10. Cleaning report and end-to-end fixture cleaning
# ---------------------------------------------------------------------------

def test_clean_observations_end_to_end(tmp_path):
    modis_csv = FIXTURES_DIR / "sample_modis.csv"
    adapter = FirmsCSVAdapter({
        "source_id": "modis_c61",
        "sensor_family": "MODIS",
        "product_version": "Collection 6.1",
        "processing_stream": "SP",
    })
    raw_df = adapter.read(modis_csv)
    canonical_df = adapter.to_canonical(raw_df)

    # Inject one row with out-of-range latitude to test flagging
    bad_row = canonical_df.iloc[0:1].copy()
    bad_row["obs_id"] = "bad_coord_row"
    bad_row["lat"] = 999.0
    test_df = pd.concat([canonical_df, bad_row], ignore_index=True)

    # Clean observations and write report
    obs_clean, report_df = clean_observations(
        test_df,
        source_id="modis_c61",
        data_dir=tmp_path,
        write_report=True,
    )

    # Verify rows are flagged, NOT deleted
    assert len(obs_clean) == len(test_df) == 4
    # The bad row is invalid
    assert bool(obs_clean.loc[obs_clean["obs_id"] == "bad_coord_row", "is_valid"].iloc[0]) is False

    # Verify cleaning_report was written to data/staging/
    report_file = tmp_path / "staging" / "cleaning_report.parquet"
    assert report_file.exists()

    saved_report = pd.read_parquet(report_file)
    assert list(saved_report.columns) == ["run_id", "rule_id", "source_id", "rows_flagged", "rows_dropped"]

    # Verify coordinate_range rule caught the 1 bad row
    coord_row = saved_report[saved_report["rule_id"] == "coordinate_range"]
    assert len(coord_row) == 1
    assert coord_row["rows_flagged"].iloc[0] == 1
    assert coord_row["rows_dropped"].iloc[0] == 0

    # Print cleaning report to verify formatting works
    print()
    print("=== Cleaning Report Output ===")
    print_cleaning_report(saved_report)
