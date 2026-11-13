"""Tests for TerraFlare pipeline runner, stages, DuckDB sync, and manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pytest

from app.api.routes_core.health import health
from app.api.routes_core.meta import get_capabilities
from app.core.pipeline import (
    compute_config_hash,
    compute_row_counts,
    determine_data_version,
    get_git_commit,
    run_pipeline,
    stage_cell_day,
    stage_clean,
    stage_harmonize,
    stage_ingest,
    stage_monthly,
    write_manifest,
)
from app.settings import settings


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with realistic FIRMS CSV fixtures."""
    firms_dir = tmp_path / "raw" / "firms"

    # MODIS fixture (request 841598)
    modis_dir = firms_dir / "841598"
    modis_dir.mkdir(parents=True, exist_ok=True)
    modis_csv = modis_dir / "fire_archive_M-C61_841598.csv"
    modis_csv.write_text(
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight,type\n"
        "28.6139,77.2090,320.5,1.0,1.0,2022-11-01,0530,Terra,MODIS,85,6.1,295.0,25.4,D,0\n"
        "28.6139,77.2090,320.5,1.0,1.0,2023-05-01,0530,Terra,MODIS,85,6.1,295.0,25.4,D,0\n"
        "28.6140,77.2095,315.0,1.0,1.0,2023-05-01,0530,Terra,MODIS,75,6.1,292.0,18.2,D,0\n"
        "15.2993,74.1240,310.0,1.0,1.0,2023-05-02,0600,Aqua,MODIS,45,6.1,290.0,12.0,D,0\n"
        "15.3000,74.1250,300.0,1.0,1.0,2023-05-02,0600,Aqua,MODIS,25,6.1,288.0,8.0,D,0\n",
        encoding="utf-8",
    )

    # VIIRS NOAA-20 fixture (request 841599)
    viirs_dir = firms_dir / "841599"
    viirs_dir.mkdir(parents=True, exist_ok=True)
    viirs_csv = viirs_dir / "fire_archive_J1V-C2_841599.csv"
    viirs_csv.write_text(
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight,type\n"
        "28.6150,77.2100,340.2,0.4,0.4,2022-11-01,0745,NOAA-20,VIIRS,h,2.0NRT,298.0,15.6,D,0\n"
        "28.6150,77.2100,340.2,0.4,0.4,2023-05-01,0745,NOAA-20,VIIRS,h,2.0NRT,298.0,15.6,D,0\n"
        "15.3050,74.1300,335.5,0.4,0.4,2023-05-02,0800,NOAA-20,VIIRS,n,2.0NRT,296.0,9.2,D,0\n"
        "15.3060,74.1310,312.0,0.4,0.4,2023-05-02,0800,NOAA-20,VIIRS,l,2.0NRT,290.0,3.1,D,0\n",
        encoding="utf-8",
    )

    return tmp_path


def test_full_pipeline_run_on_fixtures(test_data_dir: Path):
    """Test running full pipeline on fixture data produces all layers, DuckDB views, and manifest."""
    results = run_pipeline(stage="all", data_dir=test_data_dir)

    assert results["requested_stage"] == "all"
    assert results["duckdb_synced"] is True

    # 1. Raw parquet files
    raw_modis = list((test_data_dir / "raw" / "modis_c61").glob("*.parquet"))
    assert len(raw_modis) >= 1
    raw_viirs = list((test_data_dir / "raw" / "viirs_noaa20").glob("*.parquet"))
    assert len(raw_viirs) >= 1

    # 2. Canonical staging
    obs_all_files = list((test_data_dir / "staging" / "obs_all").glob("*.parquet"))
    assert len(obs_all_files) >= 2

    # 3. Cleaned staging
    obs_clean_file = test_data_dir / "staging" / "obs_clean.parquet"
    assert obs_clean_file.exists()
    obs_clean_df = pd.read_parquet(obs_clean_file)
    assert not obs_clean_df.empty
    assert "is_valid" in obs_clean_df.columns
    assert "h3_cell" in obs_clean_df.columns
    # Check that H3 cell was populated for valid rows
    valid_cells = obs_clean_df.loc[obs_clean_df["is_valid"] == True, "h3_cell"]
    assert valid_cells.notna().all()

    # 4. Cleaning report
    report_file = test_data_dir / "staging" / "cleaning_report.parquet"
    assert report_file.exists()
    report_df = pd.read_parquet(report_file)
    assert not report_df.empty

    # 5. Marts
    cell_day_file = test_data_dir / "marts" / "cell_day_activity.parquet"
    assert cell_day_file.exists()
    cell_day_df = pd.read_parquet(cell_day_file)
    assert not cell_day_df.empty
    assert "n_detections" in cell_day_df.columns

    harm_file = test_data_dir / "marts" / "harmonized_cell_day.parquet"
    assert harm_file.exists()

    monthly_file = test_data_dir / "marts" / "monthly_activity.parquet"
    assert monthly_file.exists()

    # 6. Manifest
    manifest_file = test_data_dir / "manifest.json"
    assert manifest_file.exists()
    with open(manifest_file, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    assert "data_version" in manifest
    assert "git_commit" in manifest
    assert manifest["h3_resolution"] == 6
    assert "row_counts" in manifest
    assert manifest["row_counts"]["obs_clean"] == len(obs_clean_df)
    assert manifest["row_counts"]["cell_day_activity"] == len(cell_day_df)
    assert "capabilities" in manifest
    assert manifest["capabilities"]["has_frp"] is True
    assert manifest["capabilities"]["has_confidence"] is True
    assert manifest["capabilities"]["has_day_night"] is True
    assert manifest["capabilities"]["has_platform"] is True
    assert manifest["capabilities"]["has_fire_type"] is True

    # 7. DuckDB Views
    db_file = test_data_dir / "terraflare.duckdb"
    assert db_file.exists()
    con = duckdb.connect(str(db_file))
    cnt = con.execute("SELECT count(*) FROM cell_day_activity").fetchone()[0]
    assert cnt == len(cell_day_df)
    con.close()


def test_pipeline_idempotency(test_data_dir: Path):
    """Re-running the pipeline on identical fixtures produces identical outputs and preserves version."""
    # Run 1
    run1 = run_pipeline(stage="all", data_dir=test_data_dir)
    manifest1 = run1["manifest"]
    v1 = manifest1["data_version"]
    counts1 = manifest1["row_counts"]

    obs_clean1 = pd.read_parquet(test_data_dir / "staging" / "obs_clean.parquet")

    # Run 2
    run2 = run_pipeline(stage="all", data_dir=test_data_dir)
    manifest2 = run2["manifest"]
    v2 = manifest2["data_version"]
    counts2 = manifest2["row_counts"]

    obs_clean2 = pd.read_parquet(test_data_dir / "staging" / "obs_clean.parquet")

    # Outputs and version must be identical
    assert v1 == v2
    assert counts1 == counts2
    assert len(obs_clean1) == len(obs_clean2)


def test_pipeline_sample_option(test_data_dir: Path):
    """--sample N processes at most N rows per raw file."""
    run_pipeline(stage="ingest", sample=2, data_dir=test_data_dir)

    raw_files = list((test_data_dir / "raw").glob("*/*.parquet"))
    for rf in raw_files:
        df = pd.read_parquet(rf)
        assert len(df) <= 2


def test_pipeline_individual_stages(test_data_dir: Path):
    """Each stage can be executed independently."""
    # 1. Ingest alone
    res_ingest = stage_ingest(data_dir=test_data_dir)
    assert res_ingest["stage"] == "ingest"
    assert res_ingest["rows_in"] > 0

    # 2. Clean alone
    res_clean = stage_clean(data_dir=test_data_dir)
    assert res_clean["stage"] == "clean"
    assert res_clean["rows_in"] > 0
    assert (test_data_dir / "staging" / "obs_clean.parquet").exists()

    # 3. Cell-day alone
    res_cell_day = stage_cell_day(data_dir=test_data_dir)
    assert res_cell_day["stage"] == "cell_day"
    assert res_cell_day["rows_out"] > 0
    assert (test_data_dir / "marts" / "cell_day_activity.parquet").exists()

    # 4. Harmonize alone
    res_harm = stage_harmonize(data_dir=test_data_dir)
    assert res_harm["stage"] == "harmonize"
    assert (test_data_dir / "marts" / "harmonized_cell_day.parquet").exists()

    # 5. Monthly alone
    res_monthly = stage_monthly(data_dir=test_data_dir)
    assert res_monthly["stage"] == "monthly"
    assert (test_data_dir / "marts" / "monthly_activity.parquet").exists()


def test_pipeline_filter_by_source(test_data_dir: Path):
    """Filtering by source processes only that source."""
    res = run_pipeline(stage="ingest", source="modis_c61", data_dir=test_data_dir)
    assert (test_data_dir / "raw" / "modis_c61").exists()
    assert not (test_data_dir / "raw" / "viirs_noaa20").exists()


def test_api_wired_to_manifest(test_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify /health and /meta/capabilities reflect manifest contents."""
    # Run pipeline to generate manifest
    run_pipeline(stage="all", data_dir=test_data_dir)

    # Point settings.data_dir to test_data_dir
    monkeypatch.setattr(settings, "data_dir", test_data_dir)

    manifest_path = test_data_dir / "manifest.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    expected_version = manifest["data_version"]

    # 1. Health endpoint
    h = health()
    h_data = h["data"] if isinstance(h, dict) else h
    h_meta = h["meta"] if isinstance(h, dict) else None
    assert h_data.status == "ok"
    assert (h_meta.data_version if h_meta else h_data.data_version) == expected_version
    assert h_data.manifest_summary is not None
    assert h_data.manifest_summary["data_version"] == expected_version
    assert h_data.manifest_summary["h3_resolution"] == 6

    # 2. Meta capabilities endpoint
    c = get_capabilities()
    c_data = c["data"] if isinstance(c, dict) else c
    c_meta = c["meta"] if isinstance(c, dict) else None
    assert (c_meta.data_version if c_meta else c_data.data_version) == expected_version
    assert c_data.h3_resolution == 6
    assert c_data.has_frp is True
    assert c_data.has_confidence is True
    assert c_data.has_day_night is True
    assert c_data.has_platform is True
    assert c_data.has_fire_type is True


def test_run_isolation_2023_slice_leaves_only_2023_rows(test_data_dir: Path):
    """Task 7c Run Isolation Test: running a 2023 slice after a full/sample run leaves only 2023 rows."""
    # 1. Full run across all data (including 2022 and 2023 rows)
    res_initial = run_pipeline(stage="all", data_dir=test_data_dir)
    obs_initial = pd.read_parquet(test_data_dir / "staging" / "obs_clean.parquet")
    assert (obs_initial["acq_date"].astype(str).str.startswith("2022")).any()
    assert (obs_initial["acq_date"].astype(str).str.startswith("2023")).any()

    # 2. Run 2023 slice on the same data directory
    res_2023 = run_pipeline(stage="all", year=2023, data_dir=test_data_dir)
    run_id_2023 = res_2023["run_id"]

    # 3. Assert obs_clean contains ONLY 2023 rows
    obs_clean = pd.read_parquet(test_data_dir / "staging" / "obs_clean.parquet")
    assert not obs_clean.empty
    assert (obs_clean["acq_date"].astype(str).str.startswith("2023")).all()
    assert not (obs_clean["acq_date"].astype(str).str.startswith("2022")).any()

    # 4. Assert cell_day_activity contains ONLY 2023 rows
    cell_day = pd.read_parquet(test_data_dir / "marts" / "cell_day_activity.parquet")
    assert not cell_day.empty
    assert (cell_day["date"].astype(str).str.startswith("2023")).all()
    assert not (cell_day["date"].astype(str).str.startswith("2022")).any()

    # 5. Assert cleaning_report reflects ONLY the 2023 run with run_id
    rep = pd.read_parquet(test_data_dir / "staging" / "cleaning_report.parquet")
    assert not rep.empty
    assert "run_id" in rep.columns
    assert (rep["run_id"] == run_id_2023).all()

