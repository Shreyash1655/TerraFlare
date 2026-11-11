"""Unit tests for Task 6b: processing_stream per file, cross-stream overlap deduplication, and static source masking."""

from __future__ import annotations

import json
import h3
import pandas as pd
import pytest

from app.core.cleaning.rules import check_duplicate_across_streams
from app.core.cleaning.static_mask import apply_static_source_mask, build_static_source_mask
from app.core.ingestion.adapters.firms_csv import FirmsCSVAdapter, determine_stream
from app.shared.canonical import empty_canonical_frame


# -----------------------------------------------------------------------------
# 1. Processing Stream Per File Tests
# -----------------------------------------------------------------------------

def test_determine_stream_from_filename():
    patterns = {
        "SP": "*fire_archive_*.csv",
        "NRT": "*fire_nrt_*.csv",
    }
    assert determine_stream("fire_archive_M-C61_841598.csv", stream_patterns=patterns) == "SP"
    assert determine_stream("fire_nrt_M-C61_841598.csv", stream_patterns=patterns) == "NRT"
    assert determine_stream("fire_archive_J1V-C2_841599.csv", stream_patterns=patterns) == "SP"
    assert determine_stream("fire_nrt_J1V-C2_841599.csv", stream_patterns=patterns) == "NRT"


def test_adapter_to_canonical_sets_stream_per_file():
    adapter = FirmsCSVAdapter({
        "source_id": "modis_c61",
        "sensor_family": "MODIS",
        "product_version": "C6.1",
        "processing_stream": "SP",
        "stream_patterns": {
            "SP": "*fire_archive_*.csv",
            "NRT": "*fire_nrt_*.csv",
        },
    })

    raw_df = pd.DataFrame({
        "latitude": ["28.6139"],
        "longitude": ["77.2090"],
        "acq_date": ["2023-05-01"],
        "acq_time": ["0530"],
        "satellite": ["Terra"],
        "confidence": ["85"],
    })

    # Archive file -> SP
    df_sp = adapter.to_canonical(raw_df, source_file="fire_archive_M-C61_841598.csv")
    assert df_sp["processing_stream"].iloc[0] == "SP"

    # NRT file -> NRT
    df_nrt = adapter.to_canonical(raw_df, source_file="fire_nrt_M-C61_841598.csv")
    assert df_nrt["processing_stream"].iloc[0] == "NRT"


# -----------------------------------------------------------------------------
# 2. Overlap Deduplication Across Streams Tests
# -----------------------------------------------------------------------------

def test_check_duplicate_across_streams():
    """Overlap test: when the same detection is present in both SP and NRT, keep SP and flag NRT."""
    rows = [
        # Detection 1: appears in both SP and NRT
        {
            "obs_id": "det_1",
            "source_id": "modis_c61",
            "platform": "Terra",
            "lat": 28.6139,
            "lon": 77.2090,
            "acq_date": "2023-05-01",
            "acq_time_utc": "0530",
            "processing_stream": "SP",
            "is_valid": True,
            "qc_flags": "[]",
        },
        {
            "obs_id": "det_1",
            "source_id": "modis_c61",
            "platform": "Terra",
            "lat": 28.6139,
            "lon": 77.2090,
            "acq_date": "2023-05-01",
            "acq_time_utc": "0530",
            "processing_stream": "NRT",
            "is_valid": True,
            "qc_flags": "[]",
        },
        # Detection 2: appears ONLY in SP
        {
            "obs_id": "det_2",
            "source_id": "modis_c61",
            "platform": "Terra",
            "lat": 15.2993,
            "lon": 74.1240,
            "acq_date": "2023-05-02",
            "acq_time_utc": "0600",
            "processing_stream": "SP",
            "is_valid": True,
            "qc_flags": "[]",
        },
        # Detection 3: appears ONLY in NRT
        {
            "obs_id": "det_3",
            "source_id": "modis_c61",
            "platform": "Aqua",
            "lat": 19.0760,
            "lon": 72.8777,
            "acq_date": "2023-05-03",
            "acq_time_utc": "0700",
            "processing_stream": "NRT",
            "is_valid": True,
            "qc_flags": "[]",
        },
    ]

    df = pd.DataFrame(rows)
    cleaned_df, count = check_duplicate_across_streams(df)

    assert count == 1

    # Detection 1 SP must remain valid without duplicate flag
    det1_sp = cleaned_df[(cleaned_df["obs_id"] == "det_1") & (cleaned_df["processing_stream"] == "SP")].iloc[0]
    assert det1_sp["is_valid"] == True
    assert "duplicate_across_streams" not in json.loads(det1_sp["qc_flags"])

    # Detection 1 NRT must be flagged duplicate_across_streams and marked is_valid=False
    det1_nrt = cleaned_df[(cleaned_df["obs_id"] == "det_1") & (cleaned_df["processing_stream"] == "NRT")].iloc[0]
    assert det1_nrt["is_valid"] == False
    assert "duplicate_across_streams" in json.loads(det1_nrt["qc_flags"])

    # Detection 2 SP and Detection 3 NRT must remain valid
    det2 = cleaned_df[cleaned_df["obs_id"] == "det_2"].iloc[0]
    assert det2["is_valid"] == True

    det3 = cleaned_df[cleaned_df["obs_id"] == "det_3"].iloc[0]
    assert det3["is_valid"] == True


# -----------------------------------------------------------------------------
# 3. Static Source Masking at H3 Resolution 8 Tests
# -----------------------------------------------------------------------------

def test_static_source_mask_creation_and_flagging():
    """Test static source mask at resolution 8:

    - Cells with type 2 or 3 on >= 3 distinct days qualify.
    - NRT rows in those cells are flagged 'possible_static_source' without dropping.
    """
    res8 = 8

    # Fixed coordinates
    lat_a, lon_a = 28.6139, 77.2090  # Cell A
    lat_b, lon_b = 15.2993, 74.1240  # Cell B
    lat_c, lon_c = 19.0760, 72.8777  # Cell C

    cell_a = h3.latlng_to_cell(lat_a, lon_a, res8)
    cell_b = h3.latlng_to_cell(lat_b, lon_b, res8)
    cell_c = h3.latlng_to_cell(lat_c, lon_c, res8)

    archive_rows = [
        # Cell A: type 2 on 3 distinct days -> QUALIFIES
        {"platform": "Terra", "lat": lat_a, "lon": lon_a, "acq_date": "2023-01-01", "fire_type": "2", "processing_stream": "SP"},
        {"platform": "Terra", "lat": lat_a, "lon": lon_a, "acq_date": "2023-01-02", "fire_type": "2", "processing_stream": "SP"},
        {"platform": "Terra", "lat": lat_a, "lon": lon_a, "acq_date": "2023-01-03", "fire_type": "2", "processing_stream": "SP"},

        # Cell B: type 2 on only 2 distinct days -> DOES NOT QUALIFY (< 3 days)
        {"platform": "Terra", "lat": lat_b, "lon": lon_b, "acq_date": "2023-01-01", "fire_type": "2", "processing_stream": "SP"},
        {"platform": "Terra", "lat": lat_b, "lon": lon_b, "acq_date": "2023-01-02", "fire_type": "2", "processing_stream": "SP"},

        # Cell C: type 0 (vegetation) on 4 distinct days -> DOES NOT QUALIFY (not type 2 or 3)
        {"platform": "Terra", "lat": lat_c, "lon": lon_c, "acq_date": "2023-01-01", "fire_type": "0", "processing_stream": "SP"},
        {"platform": "Terra", "lat": lat_c, "lon": lon_c, "acq_date": "2023-01-02", "fire_type": "0", "processing_stream": "SP"},
        {"platform": "Terra", "lat": lat_c, "lon": lon_c, "acq_date": "2023-01-03", "fire_type": "0", "processing_stream": "SP"},
        {"platform": "Terra", "lat": lat_c, "lon": lon_c, "acq_date": "2023-01-04", "fire_type": "0", "processing_stream": "SP"},
    ]

    archive_df = pd.DataFrame(archive_rows)
    mask = build_static_source_mask(
        archive_df,
        h3_resolution=res8,
        min_distinct_days=3,
        static_types=["2", "3"],
    )

    # Cell A must be in mask; Cell B and C must not
    assert ("Terra", cell_a) in mask
    assert ("Terra", cell_b) not in mask
    assert ("Terra", cell_c) not in mask

    # Now create NRT rows
    nrt_rows = [
        {"platform": "Terra", "lat": lat_a, "lon": lon_a, "acq_date": "2023-06-01", "processing_stream": "NRT", "is_valid": True, "qc_flags": "[]"},
        {"platform": "Terra", "lat": lat_b, "lon": lon_b, "acq_date": "2023-06-01", "processing_stream": "NRT", "is_valid": True, "qc_flags": "[]"},
        {"platform": "Terra", "lat": lat_c, "lon": lon_c, "acq_date": "2023-06-01", "processing_stream": "NRT", "is_valid": True, "qc_flags": "[]"},
    ]
    all_df = pd.concat([archive_df.assign(is_valid=True, qc_flags="[]"), pd.DataFrame(nrt_rows)], ignore_index=True)

    applied_df, nrt_flagged, archive_in_mask = apply_static_source_mask(
        all_df, mask, h3_resolution=res8
    )

    # Exactly 1 NRT row flagged (in Cell A)
    assert nrt_flagged == 1
    # Consistency check: 3 archive rows fell into Cell A
    assert archive_in_mask == 3

    # NRT in Cell A has possible_static_source flag but is_valid remains True (flag, do not drop!)
    nrt_a = applied_df[(applied_df["lat"] == lat_a) & (applied_df["processing_stream"] == "NRT")].iloc[0]
    assert nrt_a["is_valid"] == True
    assert "possible_static_source" in json.loads(nrt_a["qc_flags"])

    # NRT in Cell B and Cell C must not be flagged
    nrt_b = applied_df[(applied_df["lat"] == lat_b) & (applied_df["processing_stream"] == "NRT")].iloc[0]
    assert "possible_static_source" not in json.loads(nrt_b["qc_flags"])

