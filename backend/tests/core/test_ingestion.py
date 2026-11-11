"""Tests for FIRMS CSV adapter and ingestion pipeline (Task 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.core.ingestion.adapters.firms_csv import FirmsCSVAdapter, pad_acq_time
from app.core.ingestion.ingest import compute_file_sha256, ingest_file
from app.shared.canonical import CANONICAL_COLUMNS

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def modis_cfg():
    return {
        "source_id": "modis_c61",
        "adapter": "firms_csv",
        "sensor_family": "MODIS",
        "product_version": "Collection 6.1",
        "processing_stream": "SP",
        "platform_map": {
            "Terra": "Terra",
            "Aqua": "Aqua",
        },
    }


@pytest.fixture
def viirs_cfg():
    return {
        "source_id": "viirs_snpp",
        "adapter": "firms_csv",
        "sensor_family": "VIIRS",
        "product_version": "VIIRS C2 (S-NPP)",
        "processing_stream": "SP",
        "platform_map": {
            "SNPP": "S-NPP",
            "N20": "NOAA-20",
            "N21": "NOAA-21",
        },
    }


# ---------------------------------------------------------------------------
# 1. Time padding tests
# ---------------------------------------------------------------------------

def test_pad_acq_time_function():
    assert pad_acq_time(134) == "0134"
    assert pad_acq_time("134") == "0134"
    assert pad_acq_time(0) == "0000"
    assert pad_acq_time("0") == "0000"
    assert pad_acq_time(501) == "0501"
    assert pad_acq_time("501") == "0501"
    assert pad_acq_time(1234) == "1234"
    assert pad_acq_time("1234") == "1234"
    assert pad_acq_time(None) == "0000"


def test_time_padding_in_canonical_dataframe(modis_cfg):
    csv_file = FIXTURES_DIR / "sample_time_padding.csv"
    adapter = FirmsCSVAdapter(modis_cfg)
    raw = adapter.read(csv_file)
    canonical = adapter.to_canonical(raw)

    # 134 -> 01:34:00 UTC
    dt0 = pd.to_datetime(canonical.loc[0, "acq_datetime_utc"])
    assert dt0.hour == 1
    assert dt0.minute == 34

    # 0 -> 00:00:00 UTC
    dt1 = pd.to_datetime(canonical.loc[1, "acq_datetime_utc"])
    assert dt1.hour == 0
    assert dt1.minute == 0

    # 501 -> 05:01:00 UTC
    dt2 = pd.to_datetime(canonical.loc[2, "acq_datetime_utc"])
    assert dt2.hour == 5
    assert dt2.minute == 1

    # 1234 -> 12:34:00 UTC
    dt3 = pd.to_datetime(canonical.loc[3, "acq_datetime_utc"])
    assert dt3.hour == 12
    assert dt3.minute == 34


# ---------------------------------------------------------------------------
# 2. Missing column error test
# ---------------------------------------------------------------------------

def test_missing_column_error(modis_cfg):
    csv_file = FIXTURES_DIR / "sample_missing_col.csv"
    adapter = FirmsCSVAdapter(modis_cfg)
    raw = adapter.read(csv_file)

    with pytest.raises(ValueError) as excinfo:
        adapter.to_canonical(raw)

    err = str(excinfo.value)
    assert "Missing required column" in err
    assert "latitude" in err


# ---------------------------------------------------------------------------
# 3. Tiny fixture ingestion test
# ---------------------------------------------------------------------------

def test_tiny_fixture_ingest(tmp_path, modis_cfg):
    csv_file = FIXTURES_DIR / "sample_modis.csv"
    res = ingest_file(csv_file, modis_cfg, data_dir=tmp_path)

    assert res["source_id"] == "modis_c61"
    assert res["rows_in"] == 3
    assert Path(res["raw_parquet"]).exists()
    assert Path(res["canonical_parquet"]).exists()

    # Verify raw Parquet
    raw_df = pd.read_parquet(res["raw_parquet"])
    assert len(raw_df) == 3
    assert "latitude" in raw_df.columns
    assert "longitude" in raw_df.columns

    # Verify canonical Parquet
    can_df = pd.read_parquet(res["canonical_parquet"])
    assert len(can_df) == 3
    for col in CANONICAL_COLUMNS:
        assert col in can_df.columns, f"Missing canonical column: {col}"

    assert list(can_df["sensor_family"].unique()) == ["MODIS"]
    assert set(can_df["platform"].unique()) == {"Terra", "Aqua"}
    assert can_df["confidence_raw"].iloc[0] == "66"
    assert can_df["fire_type"].iloc[0] == "2"

    # Verify ingest_log was written
    log_path = tmp_path / "staging" / "ingest_log.parquet"
    assert log_path.exists()
    log_df = pd.read_parquet(log_path)
    assert len(log_df) == 1
    assert log_df.loc[0, "source_id"] == "modis_c61"
    assert log_df.loc[0, "rows_in"] == 3
    assert log_df.loc[0, "sha256"] == compute_file_sha256(csv_file)


# ---------------------------------------------------------------------------
# 4. VIIRS ingestion and platform mapping
# ---------------------------------------------------------------------------

def test_viirs_platform_and_confidence_mapping(tmp_path, viirs_cfg):
    csv_file = FIXTURES_DIR / "sample_viirs.csv"
    res = ingest_file(csv_file, viirs_cfg, data_dir=tmp_path)

    can_df = pd.read_parquet(res["canonical_parquet"])
    assert len(can_df) == 3

    # Platforms mapped properly: N20 -> NOAA-20, N21 -> NOAA-21, SNPP -> S-NPP
    platforms = list(can_df["platform"])
    assert platforms == ["NOAA-20", "NOAA-21", "S-NPP"]

    # Raw satellite names preserved in satellite_raw
    sat_raw = list(can_df["satellite_raw"])
    assert sat_raw == ["N20", "N21", "SNPP"]

    # Raw confidences preserved as strings
    confs = list(can_df["confidence_raw"])
    assert confs == ["n", "h", "l"]


# ---------------------------------------------------------------------------
# 5. Extras (unmapped columns) test
# ---------------------------------------------------------------------------

def test_extras_captures_unmapped_columns(modis_cfg):
    csv_file = FIXTURES_DIR / "sample_modis.csv"
    adapter = FirmsCSVAdapter(modis_cfg)
    raw = adapter.read(csv_file)
    can = adapter.to_canonical(raw)

    extras_0 = json.loads(can.loc[0, "extras"])
    assert "brightness" in extras_0
    assert "scan" in extras_0
    assert "track" in extras_0
    assert "version" in extras_0
    assert "bright_t31" in extras_0
    assert extras_0["brightness"] == "319.7"


# ---------------------------------------------------------------------------
# 6. Idempotent re-ingest test
# ---------------------------------------------------------------------------

def test_idempotent_reingest(tmp_path, modis_cfg):
    csv_file = FIXTURES_DIR / "sample_modis.csv"

    # First ingest
    res1 = ingest_file(csv_file, modis_cfg, data_dir=tmp_path)
    df1 = pd.read_parquet(res1["canonical_parquet"])
    obs_ids_1 = list(df1["obs_id"])

    # Second ingest of the exact same file
    res2 = ingest_file(csv_file, modis_cfg, data_dir=tmp_path)
    df2 = pd.read_parquet(res2["canonical_parquet"])
    obs_ids_2 = list(df2["obs_id"])

    # Rows and obs_ids must be completely identical and stable
    assert obs_ids_1 == obs_ids_2
    assert len(df1) == len(df2) == 3

    # Ingest log should not have duplicate entries for the same file
    log_df = pd.read_parquet(tmp_path / "staging" / "ingest_log.parquet")
    assert len(log_df) == 1
    assert log_df.loc[0, "rows_in"] == 3

