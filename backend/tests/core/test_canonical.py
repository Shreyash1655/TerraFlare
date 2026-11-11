"""Tests for app/shared/canonical.py – schema, dtypes, validation."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.shared.canonical import (
    CANONICAL_COLUMNS,
    CANONICAL_DTYPES,
    CanonicalObservation,
    dtypes,
    empty_canonical_frame,
)


def test_dtypes_mapping_defined():
    assert isinstance(dtypes, dict)
    assert isinstance(CANONICAL_DTYPES, dict)
    assert set(dtypes.keys()) == set(CANONICAL_COLUMNS)
    assert dtypes["lat"] == "float64"
    assert dtypes["lon"] == "float64"


def test_empty_canonical_frame_and_validate_sample_row():
    # Builds an empty canonical frame
    df = empty_canonical_frame()
    assert list(df.columns) == CANONICAL_COLUMNS
    assert len(df) == 0

    # Validates a sample row via Pydantic CanonicalObservation
    sample_data = _valid_obs()
    obs = CanonicalObservation(**sample_data)
    assert obs.lat == 15.49
    assert obs.lon == 73.82

    # Appends validated row to the frame
    row_dict = obs.model_dump()
    row_df = pd.DataFrame([row_dict])
    combined = pd.concat([df, row_df], ignore_index=True)
    assert len(combined) == 1
    assert combined.loc[0, "obs_id"] == "test-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_obs(**overrides) -> dict:
    """Return a minimal valid observation dict."""
    base = {
        "obs_id": "test-001",
        "source_id": "modis_c61",
        "sensor_family": "MODIS",
        "platform": "Terra",
        "processing_stream": "SP",
        "product_version": "Collection 6.1",
        "ingest_batch_id": "batch-2024-01",
        "acq_date": date(2023, 6, 15),
        "lat": 15.49,
        "lon": 73.82,
        "is_valid": True,
        "qc_flags": "[]",
        "is_synthetic": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Column registry tests
# ---------------------------------------------------------------------------

def test_canonical_columns_is_list_of_strings():
    assert isinstance(CANONICAL_COLUMNS, list)
    assert all(isinstance(c, str) for c in CANONICAL_COLUMNS)


def test_canonical_columns_contains_required():
    required = {
        "obs_id", "source_id", "sensor_family", "platform",
        "processing_stream", "product_version", "ingest_batch_id",
        "acq_date", "lat", "lon", "is_valid", "qc_flags", "is_synthetic",
    }
    assert required.issubset(set(CANONICAL_COLUMNS))


def test_canonical_columns_contains_optional():
    optional = {
        "acq_datetime_utc", "local_date", "h3_cell",
        "confidence_raw", "confidence_class", "frp_mw",
        "day_night", "fire_type", "satellite_raw", "instrument_raw", "extras",
    }
    assert optional.issubset(set(CANONICAL_COLUMNS))


# ---------------------------------------------------------------------------
# Empty frame tests
# ---------------------------------------------------------------------------

def test_empty_frame_has_correct_columns():
    df = empty_canonical_frame()
    assert list(df.columns) == CANONICAL_COLUMNS


def test_empty_frame_has_zero_rows():
    df = empty_canonical_frame()
    assert len(df) == 0


def test_empty_frame_lat_lon_dtype():
    df = empty_canonical_frame()
    assert df["lat"].dtype == np.float64
    assert df["lon"].dtype == np.float64


def test_empty_frame_acq_date_dtype():
    df = empty_canonical_frame()
    assert pd.api.types.is_datetime64_any_dtype(df["acq_date"])


def test_empty_frame_bool_columns():
    df = empty_canonical_frame()
    # Both bool-flagged columns should be BooleanDtype or similar nullable bool
    assert pd.api.types.is_bool_dtype(df["is_valid"]) or isinstance(
        df["is_valid"].dtype, pd.BooleanDtype
    )


# ---------------------------------------------------------------------------
# Pydantic validation – happy paths
# ---------------------------------------------------------------------------

def test_valid_observation_accepted():
    obs = CanonicalObservation(**_valid_obs())
    assert obs.obs_id == "test-001"
    assert obs.sensor_family == "MODIS"
    assert obs.platform == "Terra"
    assert obs.processing_stream == "SP"


def test_viirs_observation_accepted():
    obs = CanonicalObservation(**_valid_obs(
        obs_id="viirs-001",
        source_id="viirs_snpp",
        sensor_family="VIIRS",
        platform="S-NPP",
        processing_stream="NRT",
        product_version="VIIRS C2 (S-NPP)",
        confidence_raw="nominal",
        confidence_class="nominal",
    ))
    assert obs.sensor_family == "VIIRS"
    assert obs.platform == "S-NPP"
    assert obs.processing_stream == "NRT"
    assert obs.confidence_raw == "nominal"


def test_optional_fields_default_to_none():
    obs = CanonicalObservation(**_valid_obs())
    assert obs.h3_cell is None
    assert obs.local_date is None
    assert obs.acq_datetime_utc is None
    assert obs.confidence_raw is None
    assert obs.confidence_class is None
    assert obs.frp_mw is None
    assert obs.day_night is None
    assert obs.fire_type is None
    assert obs.satellite_raw is None
    assert obs.instrument_raw is None
    assert obs.extras is None


def test_frp_zero_is_valid():
    obs = CanonicalObservation(**_valid_obs(frp_mw=0.0))
    assert obs.frp_mw == 0.0


def test_all_platforms_accepted():
    for platform in ("Terra", "Aqua", "S-NPP", "NOAA-20", "NOAA-21"):
        sensor = "MODIS" if platform in ("Terra", "Aqua") else "VIIRS"
        obs = CanonicalObservation(**_valid_obs(platform=platform, sensor_family=sensor))
        assert obs.platform == platform


def test_confidence_classes_accepted():
    for cls in ("low", "nominal", "high", "unknown"):
        obs = CanonicalObservation(**_valid_obs(confidence_class=cls))
        assert obs.confidence_class == cls


def test_day_night_accepted():
    for dn in ("D", "N"):
        obs = CanonicalObservation(**_valid_obs(day_night=dn))
        assert obs.day_night == dn


def test_qc_flags_json():
    flags = json.dumps(["out_of_region", "low_frp"])
    obs = CanonicalObservation(**_valid_obs(qc_flags=flags))
    assert obs.qc_flags == flags


def test_is_synthetic_true_for_fixture():
    obs = CanonicalObservation(**_valid_obs(is_synthetic=True))
    assert obs.is_synthetic is True


# ---------------------------------------------------------------------------
# Pydantic validation – rejections
# ---------------------------------------------------------------------------

def test_invalid_latitude_too_high():
    with pytest.raises(ValidationError) as exc_info:
        CanonicalObservation(**_valid_obs(lat=91.0))
    assert "lat" in str(exc_info.value).lower()


def test_invalid_latitude_too_low():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(lat=-90.1))


def test_invalid_longitude_too_high():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(lon=180.1))


def test_invalid_longitude_too_low():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(lon=-181.0))


def test_invalid_sensor_family_rejected():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(sensor_family="Landsat"))


def test_invalid_platform_rejected():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(platform="Sentinel-2"))


def test_invalid_processing_stream_rejected():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(processing_stream="ARCHIVE"))


def test_invalid_confidence_class_rejected():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(confidence_class="medium"))


def test_negative_frp_rejected():
    with pytest.raises(ValidationError):
        CanonicalObservation(**_valid_obs(frp_mw=-1.0))


def test_missing_required_field_raises():
    data = _valid_obs()
    del data["obs_id"]
    with pytest.raises(ValidationError):
        CanonicalObservation(**data)


def test_missing_lat_raises():
    data = _valid_obs()
    del data["lat"]
    with pytest.raises(ValidationError):
        CanonicalObservation(**data)

