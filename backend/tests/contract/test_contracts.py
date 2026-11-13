"""Contract tests validating contracts/examples/*.json for frontend (Member 2).

Ensures all example responses conform to the {data, meta} envelope and contain
accurate, real metadata and data types.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

EXAMPLES_DIR = Path("contracts/examples")


@pytest.fixture
def example_files():
    assert EXAMPLES_DIR.exists(), f"Examples directory {EXAMPLES_DIR} does not exist"
    files = list(EXAMPLES_DIR.glob("*.json"))
    assert len(files) >= 11, f"Expected at least 11 JSON example contracts, found {len(files)}"
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in files}


def test_all_json_examples_have_standard_envelope(example_files):
    """Every example contract MUST have top-level 'data' and 'meta' keys."""
    required_meta_keys = {
        "data_version",
        "series",
        "method",
        "is_provisional",
        "reliability",
        "warnings",
        "generated_at",
    }
    for name, content in example_files.items():
        assert "data" in content, f"{name}.json missing 'data' key"
        assert "meta" in content, f"{name}.json missing 'meta' key"
        meta = content["meta"]
        assert isinstance(meta, dict), f"{name}.json 'meta' must be a JSON object"
        missing = required_meta_keys - set(meta.keys())
        assert not missing, f"{name}.json meta missing fields: {missing}"
        assert isinstance(meta["warnings"], list), f"{name}.json meta.warnings must be a list"
        assert isinstance(meta["is_provisional"], bool), f"{name}.json meta.is_provisional must be bool"
        assert isinstance(meta["generated_at"], str), f"{name}.json meta.generated_at must be string"


def test_health_contract(example_files):
    contract = example_files["health"]
    data = contract["data"]
    assert data["status"] == "ok"
    assert "service" in data


def test_capabilities_contract(example_files):
    contract = example_files["meta_capabilities"]
    data = contract["data"]
    assert "MODIS" in data["sensors"]
    assert "VIIRS" in data["sensors"]
    assert "harmonized" in data["supported_series"]
    assert "Aqua" in data["platforms"]


def test_regions_contract(example_files):
    contract = example_files["regions"]
    data = contract["data"]
    assert "regions" in data
    regions = data["regions"]
    assert len(regions) > 0
    first = regions[0]
    assert "region_id" in first
    assert "name" in first
    assert "bbox" in first
    assert len(first["bbox"]) == 4


def test_hotspots_contract(example_files):
    contract = example_files["hotspots"]
    data = contract["data"]
    assert data.get("type") == "FeatureCollection"
    assert "features" in data
    if data["features"]:
        feat = data["features"][0]
        assert feat.get("type") == "Feature"
        assert "geometry" in feat
        assert "properties" in feat
        props = feat["properties"]
        assert "sensor_family" in props or "sensor" in props
        assert "is_provisional" in props


def test_hotspots_cells_contract(example_files):
    contract = example_files["hotspots_cells"]
    data = contract["data"]
    assert "cells" in data
    assert "h3_resolution" in data
    if data["cells"]:
        cell = data["cells"][0]
        assert "h3_cell" in cell
        assert "harmonized_value" in cell
        assert "is_provisional" in cell


def test_calendar_contract(example_files):
    contract = example_files["calendar"]
    data = contract["data"]
    assert "days" in data
    assert "year" in data
    if data["days"]:
        day = data["days"][0]
        assert "date" in day
        assert "harmonized_value" in day
        assert "is_provisional" in day
        assert "is_partial" in day
        assert "days_covered" in day
        assert "days_in_month" in day


def test_history_yearly_contract(example_files):
    contract = example_files["history_yearly"]
    data = contract["data"]
    assert "years" in data
    years = data["years"]
    assert len(years) > 0
    first = years[0]
    assert "year" in first
    assert "harmonized_value" in first
    assert "is_provisional" in first
    assert "is_partial" in first
    assert "days_covered" in first
    assert "days_in_month" in first


def test_history_monthly_contract(example_files):
    contract = example_files["history_monthly"]
    data = contract["data"]
    assert "matrix" in data
    matrix = data["matrix"]
    assert len(matrix) > 0
    first = matrix[0]
    assert "year_month" in first
    assert "harmonized_value" in first
    assert "is_provisional" in first
    assert "is_partial" in first
    assert "days_covered" in first
    assert "days_in_month" in first


def test_history_current_vs_median_contract(example_files):
    contract = example_files["history_current_vs_median"]
    data = contract["data"]
    assert "ratio" in data or "ratio_to_median" in data
    assert "median" in data
    assert "current" in data
    assert "reliability" in data
    assert "is_partial" in data
    assert "is_provisional" in data


def test_harmonization_comparison_contract(example_files):
    contract = example_files["harmonization_comparison"]
    data = contract["data"]
    assert "series" in data
    series = data["series"]
    assert len(series) > 0
    first = series[0]
    assert "period" in first
    assert "modis_observed" in first
    assert "viirs_observed" in first
    assert "harmonized_value" in first


def test_harmonization_method_contract(example_files):
    contract = example_files["harmonization_method"]
    data = contract["data"]
    assert "method_id" in data
    assert "name" in data
    assert "description" in data


def test_export_sample_csv():
    csv_path = EXAMPLES_DIR / "export_sample.csv"
    assert csv_path.exists(), "export_sample.csv does not exist"
    lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 2
    assert lines[0].startswith("#")
    header_line = next(l for l in lines if not l.startswith("#"))
    cols = [c.strip() for c in header_line.split(",")]
    assert "sensor" in cols
    assert "platform" in cols
    assert "value_type" in cols
    assert "is_provisional" in cols
    assert "is_partial" in cols
    assert "days_covered" in cols
    assert "days_in_month" in cols
