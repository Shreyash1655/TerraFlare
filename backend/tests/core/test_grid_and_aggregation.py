"""Tests for H3 spatial grid assignment, cell-day aggregation, and DuckDB repository (Task 5)."""

from __future__ import annotations

import time
from datetime import date, datetime
from pathlib import Path

import h3
import pandas as pd
import pytest

from app.core.harmonization.temporal import (
    aggregate_cell_day_activity,
    count_unique_active_cells_per_platform_day,
)
from app.core.spatial.grid import assign_h3_cells, bbox_to_cells, polygon_to_cells
from app.core.storage.duckdb_repo import DuckDBRepository
from app.core.storage.parquet_io import write_mart, write_parquet
from app.shared.regions import BBox


# ---------------------------------------------------------------------------
# 1. Spatial Grid tests
# ---------------------------------------------------------------------------

def test_assign_h3_cells_unique_mapping():
    df = pd.DataFrame({
        "lat": [15.5, 15.5, 18.5, 28.5, None],
        "lon": [73.8, 73.8, 73.8, 77.2, None],
    })
    out = assign_h3_cells(df, resolution=6)
    assert "h3_cell" in out.columns
    assert len(out) == 5

    # Check that identical lat/lon got identical H3 cells
    assert out.loc[0, "h3_cell"] == out.loc[1, "h3_cell"]
    assert out.loc[0, "h3_cell"] == h3.latlng_to_cell(15.5, 73.8, 6)

    # Distinct coordinates produce distinct cells
    assert out.loc[0, "h3_cell"] != out.loc[2, "h3_cell"]
    assert out.loc[2, "h3_cell"] != out.loc[3, "h3_cell"]

    # None coordinate results in None
    assert out.loc[4, "h3_cell"] is None


def test_bbox_to_cells_h3_v4():
    # Small test bbox in Goa: [min_lon, min_lat, max_lon, max_lat]
    bbox = [73.8, 15.4, 73.9, 15.5]
    cells = bbox_to_cells(bbox, resolution=6)
    assert isinstance(cells, set)
    assert len(cells) > 0
    # Every element is a valid H3 cell string
    sample_cell = next(iter(cells))
    assert h3.is_valid_cell(sample_cell)


def test_bbox_to_cells_accepts_bbox_dataclass():
    bbox = BBox(min_lon=73.8, min_lat=15.4, max_lon=73.9, max_lat=15.5)
    cells = bbox_to_cells(bbox, resolution=6)
    assert isinstance(cells, set)
    assert len(cells) > 0


def test_polygon_to_cells_geojson_dict():
    geojson_poly = {
        "type": "Polygon",
        "coordinates": [
            [[73.8, 15.4], [73.9, 15.4], [73.9, 15.5], [73.8, 15.5], [73.8, 15.4]]
        ],
    }
    cells = polygon_to_cells(geojson_poly, resolution=6)
    assert isinstance(cells, set)
    assert len(cells) > 0


# ---------------------------------------------------------------------------
# 2. Hand-made fixture: 2 platforms, 3 cells
# ---------------------------------------------------------------------------

@pytest.fixture
def handmade_fixture_data():
    """Build a known dataset with 2 platforms, 3 cells, and 1 invalid row.

    Platform 1: Terra (MODIS, source_id: modis_c61)
      - Cell 1 (lat 15.50, lon 73.80):
          Row 1: frp=10.0, conf='high'
          Row 2: frp=20.0, conf='nominal'
          -> Total: 2 detections, 1 high_conf, sum_frp=30.0, max_frp=20.0
      - Cell 2 (lat 18.50, lon 73.80):
          Row 3: frp=15.0, conf='high'
          -> Total: 1 detection, 1 high_conf, sum_frp=15.0, max_frp=15.0

    Platform 2: S-NPP (VIIRS, source_id: viirs_snpp)
      - Cell 1 (lat 15.50, lon 73.80):
          Row 4: frp=5.0, conf='high'
          -> Total: 1 detection, 1 high_conf, sum_frp=5.0, max_frp=5.0
      - Cell 3 (lat 28.50, lon 77.20):
          Row 5: frp=25.0, conf='nominal'
          Row 6: frp=35.0, conf='high'
          Row 7: frp=40.0, conf='high'
          -> Total: 3 detections, 2 high_conf, sum_frp=100.0, max_frp=40.0
      - Invalid row in Cell 3 (lat 28.50, lon 77.20):
          Row 8: frp=999.0, is_valid=False (must be excluded from aggregation)
    """
    rows = [
        # Terra - Cell 1
        {
            "obs_id": "terra_1",
            "source_id": "modis_c61",
            "sensor_family": "MODIS",
            "platform": "Terra",
            "processing_stream": "SP",
            "product_version": "C6.1",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 15.50,
            "lon": 73.80,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "high",
            "frp_mw": 10.0,
            "day_night": "D",
        },
        {
            "obs_id": "terra_2",
            "source_id": "modis_c61",
            "sensor_family": "MODIS",
            "platform": "Terra",
            "processing_stream": "SP",
            "product_version": "C6.1",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 15.50,
            "lon": 73.80,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "nominal",
            "frp_mw": 20.0,
            "day_night": "D",
        },
        # Terra - Cell 2
        {
            "obs_id": "terra_3",
            "source_id": "modis_c61",
            "sensor_family": "MODIS",
            "platform": "Terra",
            "processing_stream": "SP",
            "product_version": "C6.1",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 18.50,
            "lon": 73.80,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "high",
            "frp_mw": 15.0,
            "day_night": "D",
        },
        # S-NPP - Cell 1
        {
            "obs_id": "snpp_1",
            "source_id": "viirs_snpp",
            "sensor_family": "VIIRS",
            "platform": "S-NPP",
            "processing_stream": "SP",
            "product_version": "C2",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 15.50,
            "lon": 73.80,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "high",
            "frp_mw": 5.0,
            "day_night": "D",
        },
        # S-NPP - Cell 3
        {
            "obs_id": "snpp_2",
            "source_id": "viirs_snpp",
            "sensor_family": "VIIRS",
            "platform": "S-NPP",
            "processing_stream": "SP",
            "product_version": "C2",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 28.50,
            "lon": 77.20,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "nominal",
            "frp_mw": 25.0,
            "day_night": "D",
        },
        {
            "obs_id": "snpp_3",
            "source_id": "viirs_snpp",
            "sensor_family": "VIIRS",
            "platform": "S-NPP",
            "processing_stream": "SP",
            "product_version": "C2",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 28.50,
            "lon": 77.20,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "high",
            "frp_mw": 35.0,
            "day_night": "D",
        },
        {
            "obs_id": "snpp_4",
            "source_id": "viirs_snpp",
            "sensor_family": "VIIRS",
            "platform": "S-NPP",
            "processing_stream": "SP",
            "product_version": "C2",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 28.50,
            "lon": 77.20,
            "is_valid": True,
            "qc_flags": "[]",
            "confidence_class": "high",
            "frp_mw": 40.0,
            "day_night": "D",
        },
        # Invalid row - should be excluded
        {
            "obs_id": "invalid_1",
            "source_id": "viirs_snpp",
            "sensor_family": "VIIRS",
            "platform": "S-NPP",
            "processing_stream": "SP",
            "product_version": "C2",
            "ingest_batch_id": "b1",
            "acq_date": date(2023, 6, 15),
            "local_date": date(2023, 6, 15),
            "lat": 28.50,
            "lon": 77.20,
            "is_valid": False,
            "qc_flags": "['invalid_coordinates']",
            "confidence_class": "high",
            "frp_mw": 999.0,
            "day_night": "D",
        },
    ]
    df = pd.DataFrame(rows)
    df = assign_h3_cells(df, resolution=6)
    return df


def test_hand_calculated_cell_day_counts(handmade_fixture_data):
    df = handmade_fixture_data
    cell1 = h3.latlng_to_cell(15.50, 73.80, 6)
    cell2 = h3.latlng_to_cell(18.50, 73.80, 6)
    cell3 = h3.latlng_to_cell(28.50, 77.20, 6)

    agg = aggregate_cell_day_activity(df, date_col="local_date", valid_only=True)

    # Exactly 4 groups
    assert len(agg) == 4

    # 1. Terra in Cell 1
    t_c1 = agg[(agg["platform"] == "Terra") & (agg["h3_cell"] == cell1)]
    assert len(t_c1) == 1
    assert t_c1["n_detections"].iloc[0] == 2
    assert t_c1["n_high_conf"].iloc[0] == 1
    assert t_c1["frp_sum_mw"].iloc[0] == 30.0
    assert t_c1["frp_max_mw"].iloc[0] == 20.0

    # 2. Terra in Cell 2
    t_c2 = agg[(agg["platform"] == "Terra") & (agg["h3_cell"] == cell2)]
    assert len(t_c2) == 1
    assert t_c2["n_detections"].iloc[0] == 1
    assert t_c2["n_high_conf"].iloc[0] == 1
    assert t_c2["frp_sum_mw"].iloc[0] == 15.0
    assert t_c2["frp_max_mw"].iloc[0] == 15.0

    # 3. S-NPP in Cell 1
    s_c1 = agg[(agg["platform"] == "S-NPP") & (agg["h3_cell"] == cell1)]
    assert len(s_c1) == 1
    assert s_c1["n_detections"].iloc[0] == 1
    assert s_c1["n_high_conf"].iloc[0] == 1
    assert s_c1["frp_sum_mw"].iloc[0] == 5.0
    assert s_c1["frp_max_mw"].iloc[0] == 5.0

    # 4. S-NPP in Cell 3
    s_c3 = agg[(agg["platform"] == "S-NPP") & (agg["h3_cell"] == cell3)]
    assert len(s_c3) == 1
    assert s_c3["n_detections"].iloc[0] == 3
    assert s_c3["n_high_conf"].iloc[0] == 2
    assert s_c3["frp_sum_mw"].iloc[0] == 100.0
    assert s_c3["frp_max_mw"].iloc[0] == 40.0


def test_unique_active_cells_helper(handmade_fixture_data):
    df = handmade_fixture_data
    agg = aggregate_cell_day_activity(df, date_col="local_date", valid_only=True)
    active = count_unique_active_cells_per_platform_day(agg, date_col="date")

    assert len(active) == 2
    terra_active = active[active["platform"] == "Terra"]["n_active_cells"].iloc[0]
    snpp_active = active[active["platform"] == "S-NPP"]["n_active_cells"].iloc[0]

    # Terra had Cell 1 and Cell 2 -> 2 active cells
    assert terra_active == 2
    # S-NPP had Cell 1 and Cell 3 -> 2 active cells
    assert snpp_active == 2


# ---------------------------------------------------------------------------
# 3. DuckDB Storage and Repository Acceptance Tests (< 1 second)
# ---------------------------------------------------------------------------

def test_duckdb_repository_on_fixture(tmp_path, handmade_fixture_data):
    # 1. Write clean observations to staging
    obs_file = tmp_path / "staging" / "obs_clean.parquet"
    write_parquet(handmade_fixture_data, obs_file)

    # 2. Write aggregated mart to data/marts/cell_day_activity.parquet
    cell_day_df = aggregate_cell_day_activity(handmade_fixture_data, valid_only=True)
    write_mart(cell_day_df, "cell_day_activity", data_dir=tmp_path)

    # 3. Initialize repository
    repo = DuckDBRepository(data_dir=tmp_path)

    # 4. Measure query speed (must be under 1.0 second)
    t0 = time.perf_counter()
    queried_cell_day = repo.get_cell_day()
    query_duration = time.perf_counter() - t0

    assert query_duration < 1.0, f"Query took too long: {query_duration:.3f}s"
    assert len(queried_cell_day) == 4

    # Check MODIS / VIIRS sensor filters
    modis_only = repo.get_cell_day(sensors=["MODIS"])
    assert len(modis_only) == 2
    assert set(modis_only["platform"]) == {"Terra"}

    viirs_only = repo.get_cell_day(sensors=["VIIRS"])
    assert len(viirs_only) == 2
    assert set(viirs_only["platform"]) == {"S-NPP"}

    # Query observations
    obs = repo.get_observations(valid_only=True)
    assert len(obs) == 7  # 7 valid rows, excluding the 1 invalid row

    # Query capabilities & empty frames
    caps = repo.get_capabilities()
    assert "MODIS" in caps["sensors"]
    assert caps["h3_resolution"] == 6

    empty_harm = repo.get_harmonized()
    assert isinstance(empty_harm, pd.DataFrame)
    assert "harmonized_value" in empty_harm.columns


def test_assign_h3_cells_nan_handling():
    """Ensure missing/invalid coordinates are explicitly cast/replaced with None."""
    df = pd.DataFrame({
        "lat": [28.6139, float("nan"), None, 15.2993],
        "lon": [77.2090, 77.2090, None, float("nan")],
    })
    res = assign_h3_cells(df, resolution=6)
    assert res.loc[0, "h3_cell"] is not None
    assert res.loc[1, "h3_cell"] is None
    assert res.loc[2, "h3_cell"] is None
    assert res.loc[3, "h3_cell"] is None
    assert res["h3_cell"].dtype == object


