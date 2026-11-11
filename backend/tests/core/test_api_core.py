"""Unit and contract tests for Core API endpoints (/api/v1)."""

from __future__ import annotations

import os

os.environ["TERRAFLARE_DATA_MODE"] = "fixture"

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_regions():
    """Verify /api/v1/regions returns list of regions with bboxes."""
    resp = client.get("/api/v1/regions")
    assert resp.status_code == 200
    data = resp.json()
    assert "regions" in data
    assert len(data["regions"]) > 0
    region_ids = [r["region_id"] for r in data["regions"]]
    assert "india" in region_ids

    # Check structure
    ind = next(r for r in data["regions"] if r["region_id"] == "india")
    assert ind["name"] == "India"
    assert len(ind["bbox"]) == 4
    min_lon, min_lat, max_lon, max_lat = ind["bbox"]
    assert min_lon < max_lon and min_lat < max_lat


def test_get_hotspots_geojson():
    """Verify /api/v1/hotspots returns valid GeoJSON FeatureCollection."""
    resp = client.get("/api/v1/hotspots?region_id=india&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert "truncated" in data
    assert "features" in data
    assert isinstance(data["features"], list)

    if data["features"]:
        feat = data["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        assert len(feat["geometry"]["coordinates"]) == 2
        props = feat["properties"]
        assert "obs_id" in props
        assert "sensor_family" in props
        assert "platform" in props
        assert "confidence_class" in props
        assert "is_provisional" in props


def test_get_hotspots_drawn_area_uncertainty_and_warning():
    """Verify Task 10 addendum: interval_for, reliability label, and small area warning."""
    # Tiny drawn bounding box
    tiny_bbox = "77.10,28.60,77.11,28.61"
    resp = client.get(f"/api/v1/hotspots?bbox={tiny_bbox}")
    assert resp.status_code == 200
    data = resp.json()
    assert "reliability" in data
    assert data["reliability"] in ("high", "medium", "low")
    assert "uncertainty_interval" in data
    # Small area warning should be present when expected count < 10 or reliability == 'low'
    assert "warning" in data
    assert "Area is small" in data["warning"]


def test_get_hotspot_cells():
    """Verify /api/v1/hotspots/cells returns H3 cell aggregations."""
    resp = client.get("/api/v1/hotspots/cells?region_id=india&h3_res=6")
    assert resp.status_code == 200
    data = resp.json()
    assert "h3_resolution" in data
    assert data["h3_resolution"] == 6
    assert "cells" in data
    assert isinstance(data["cells"], list)


def test_get_calendar():
    """Verify /api/v1/calendar returns 365 daily values for a region and year."""
    resp = client.get("/api/v1/calendar?region_id=india&year=2022")
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2022
    assert data["region_id"] == "india"
    assert "unit" in data
    assert len(data["days"]) == 365
    day1 = data["days"][0]
    assert day1["date"] == "2022-01-01"
    assert "harmonized_value" in day1
    assert "data_flag" in day1
    assert "is_provisional" in day1


def test_get_history_yearly():
    """Verify /api/v1/history/yearly returns annual totals and sensor mix."""
    resp = client.get("/api/v1/history/yearly?region_id=india")
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_id"] == "india"
    assert "years" in data
    assert isinstance(data["years"], list)
    if data["years"]:
        yr = data["years"][0]
        assert "year" in yr
        assert "harmonized_value" in yr
        assert "modis_observed" in yr
        assert "viirs_observed" in yr
        assert "sensor_mix" in yr


def test_get_history_monthly():
    """Verify /api/v1/history/monthly returns year x month matrix."""
    resp = client.get("/api/v1/history/monthly?region_id=india")
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_id"] == "india"
    assert "matrix" in data
    assert isinstance(data["matrix"], list)
    if data["matrix"]:
        item = data["matrix"][0]
        assert "year" in item
        assert "month" in item
        assert "harmonized_value" in item
        assert "is_provisional" in item


def test_get_history_current_vs_median():
    """Verify /api/v1/history/current-vs-median returns benchmark comparison."""
    resp = client.get("/api/v1/history/current-vs-median?region_id=india")
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_id"] == "india"
    assert "current" in data
    assert "median" in data
    assert "q25" in data
    assert "q75" in data
    assert "n_baseline_years" in data


def test_get_harmonization_comparison():
    """Verify /api/v1/harmonization/comparison returns aligned series and diagnostics."""
    resp = client.get("/api/v1/harmonization/comparison?region_id=india&granularity=week")
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_id"] == "india"
    assert data["granularity"] == "week"
    assert "series" in data
    assert "diagnostics" in data
    diag = data["diagnostics"]
    assert "overlap_period" in diag
    assert "start" in diag["overlap_period"]
    assert "end" in diag["overlap_period"]


def test_get_harmonization_method():
    """Verify /api/v1/harmonization/method returns transparent methodology and validation."""
    resp = client.get("/api/v1/harmonization/method")
    assert resp.status_code == 200
    data = resp.json()
    assert "method_id" in data
    assert "name" in data
    assert "description" in data
    assert "overlap_period" in data
    assert "assumptions" in data
    assert len(data["assumptions"]) > 0
    assert "limitations" in data
    assert len(data["limitations"]) > 0
    assert "validation" in data
    assert len(data["validation"]) > 0


def test_get_export_csv():
    """Verify /api/v1/export/csv streams valid CSV for each dataset type."""
    for ds in ["monthly", "calendar", "hotspots", "comparison"]:
        resp = client.get(f"/api/v1/export/csv?dataset={ds}&region_id=india")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert f'filename="terraflare_{ds}_india.csv"' in resp.headers["content-disposition"]
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 1  # Header must be present

