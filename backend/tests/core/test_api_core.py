"""Unit and contract tests for Core API endpoints (/api/v1) with common {data, meta} envelope."""

from __future__ import annotations

import os

os.environ["TERRAFLARE_DATA_MODE"] = "fixture"

import pytest
from fastapi.testclient import TestClient

from app.api.routes_core.calendar import get_calendar
from app.api.routes_core.export import export_csv
from app.api.routes_core.harmonization import get_comparison, get_harmonization_method
from app.api.routes_core.health import health
from app.api.routes_core.history import (
    get_current_vs_median,
    get_monthly_history,
    get_yearly_history,
)
from app.api.routes_core.hotspots import get_hotspot_cells, get_hotspots
from app.api.routes_core.meta import get_capabilities
from app.api.routes_core.regions import get_regions
from app.main import app
from app.shared.errors import TerraFlareError

client = TestClient(app)


def test_get_health():
    """Verify /api/v1/health returns {data, meta} envelope."""
    resp = health()
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    meta = resp["meta"]
    assert data.status == "ok"
    assert hasattr(meta, "generated_at")
    assert hasattr(meta, "data_version")


def test_get_capabilities():
    """Verify /api/v1/meta/capabilities returns capabilities in common envelope."""
    resp = get_capabilities()
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert "MODIS" in data.sensors
    assert "VIIRS" in data.sensors
    assert "harmonized" in data.supported_series


def test_get_regions():
    """Verify /api/v1/regions returns list of regions with bboxes inside {data, meta}."""
    resp = get_regions()
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert len(data.regions) > 0
    region_ids = [r.region_id for r in data.regions]
    assert "india" in region_ids

    ind = next(r for r in data.regions if r.region_id == "india")
    assert ind.name == "India"
    assert len(ind.bbox) == 4
    min_lon, min_lat, max_lon, max_lat = ind.bbox
    assert min_lon < max_lon and min_lat < max_lat


def test_get_hotspots_geojson():
    """Verify /api/v1/hotspots returns valid GeoJSON FeatureCollection in {data, meta}."""
    resp = get_hotspots(region_id="india", limit=10)
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    meta = resp["meta"]
    assert data["type"] == "FeatureCollection"
    assert "truncated" in data
    assert "features" in data
    assert isinstance(data["features"], list)
    assert hasattr(meta, "generated_at")
    assert hasattr(meta, "is_provisional")


def test_get_hotspots_drawn_area_uncertainty_and_warning():
    """Verify Task 10: interval_for, reliability label, and small area warning."""
    tiny_bbox = "77.10,28.60,77.11,28.61"
    resp = get_hotspots(bbox=tiny_bbox)
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    meta = resp["meta"]
    assert meta.reliability in ("high", "medium", "low", "insufficient")
    assert "uncertainty_interval" in data
    assert len(meta.warnings) > 0
    assert any("Area is small" in w for w in meta.warnings)


def test_get_hotspot_cells():
    """Verify /api/v1/hotspots/cells returns H3 cell aggregations in {data, meta}."""
    resp = get_hotspot_cells(region_id="india", h3_res=6)
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert data["h3_resolution"] == 6
    assert isinstance(data["cells"], list)


def test_get_calendar():
    """Verify /api/v1/calendar returns 365 daily values in {data, meta}."""
    resp = get_calendar(region_id="india", year=2022)
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert data.year == 2022
    assert data.unit == "detections"
    assert len(data.days) == 365
    day1 = data.days[0]
    assert day1.date == "2022-01-01"
    assert hasattr(day1, "harmonized_value")
    assert hasattr(day1, "data_flag")
    assert hasattr(day1, "is_provisional")


def test_get_history_yearly():
    """Verify /api/v1/history/yearly returns annual totals and sensor mix in {data, meta}."""
    resp = get_yearly_history(region_id="india")
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert isinstance(data.years, list)
    if data.years:
        yr = data.years[0]
        assert hasattr(yr, "year")
        assert hasattr(yr, "harmonized_value")
        assert hasattr(yr, "modis_observed")
        assert hasattr(yr, "viirs_observed")
        assert hasattr(yr, "sensor_mix")


def test_get_history_monthly():
    """Verify /api/v1/history/monthly returns year x month matrix in {data, meta}."""
    resp = get_monthly_history(region_id="india")
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert isinstance(data.matrix, list)
    if data.matrix:
        item = data.matrix[0]
        assert hasattr(item, "year")
        assert hasattr(item, "month")
        assert hasattr(item, "harmonized_value")
        assert hasattr(item, "is_provisional")


def test_get_history_current_vs_median():
    """Verify /api/v1/history/current-vs-median returns benchmark comparison in {data, meta}."""
    resp = get_current_vs_median(region_id="india")
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert hasattr(data, "current")
    assert hasattr(data, "median")
    assert hasattr(data, "q25")
    assert hasattr(data, "q75")
    assert hasattr(data, "n_baseline_years")


def test_get_harmonization_comparison():
    """Verify /api/v1/harmonization/comparison returns aligned series in {data, meta}."""
    resp = get_comparison(region_id="india", granularity="week")
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert data.granularity == "week"
    assert isinstance(data.series, list)
    assert hasattr(data.diagnostics, "overlap_period")


def test_get_harmonization_method():
    """Verify /api/v1/harmonization/method returns transparent methodology in {data, meta}."""
    resp = get_harmonization_method()
    assert "data" in resp
    assert "meta" in resp
    data = resp["data"]
    assert data.method_id in ("stratified_ratio", "identity")
    assert len(data.assumptions) > 0
    assert len(data.limitations) > 0
    assert len(data.validation) > 0


def test_get_export_csv():
    """Verify /api/v1/export/csv streams CSV with metadata block and required columns."""
    for ds in ["monthly", "calendar", "hotspots", "comparison"]:
        resp = export_csv(dataset=ds, region_id="india", start="2026-11-01")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert f'filename="terraflare_{ds}_india.csv"' in resp.headers["content-disposition"]

        content = resp.raw_content.decode("utf-8")
        lines = content.strip().split("\n")
        # Must have metadata block comment at start
        assert lines[0].startswith("#")
        # Find header line (first non-comment line)
        header_line = next(l for l in lines if not l.startswith("#"))
        assert "sensor" in header_line
        assert "platform" in header_line
        assert "value_type" in header_line
        assert "is_provisional" in header_line


def test_area_validation_outside_data_region():
    """Verify area outside data region is rejected with a clear message."""
    # Bounding box in North America (far outside India)
    with pytest.raises(TerraFlareError) as exc_info:
        get_hotspots(bbox="-120.0,30.0,-119.0,31.0")
    assert exc_info.value.status_code == 400
    assert "outside the supported data region" in exc_info.value.message


def test_area_validation_oversized_area():
    """Verify oversized area is rejected with a clear message."""
    # Huge bounding box spanning 40 degrees
    with pytest.raises(TerraFlareError) as exc_info:
        get_hotspots(bbox="60.0,0.0,105.0,40.0")
    assert exc_info.value.status_code == 400
    assert "oversized" in exc_info.value.message.lower()


def test_drawn_area_small_fallback_composite_splicing():
    """Verify small drawn area fallback: pre-2012 uses native MODIS and 2012+ uses observed VIIRS without dropping pre-2012."""
    small_bbox = "76.0,30.0,76.1,30.1"
    resp = get_yearly_history(bbox=small_bbox, series="harmonized")
    data = resp["data"]
    meta = resp["meta"]
    assert meta.series == "harmonized"
    assert meta.reliability in ("low", "insufficient")
    # Pre-2012 years must NOT be silently dropped!
    years = [y.year for y in data.years]
    assert any(yr < 2012 for yr in years)
    assert any("Small area" in w for w in meta.warnings)
    assert any("Area is small" in w for w in meta.warnings)


def test_cors_configuration():
    """Verify CORS configuration for http://localhost:5173."""
    from starlette.middleware.cors import CORSMiddleware
    from app.settings import settings

    assert "http://localhost:5173" in settings.cors_origins
    cors_m = next((m for m in app.user_middleware if m.cls == CORSMiddleware), None)
    assert cors_m is not None
    assert "http://localhost:5173" in cors_m.kwargs["allow_origins"]
    assert cors_m.kwargs["allow_credentials"] is False
    assert "GET" in cors_m.kwargs["allow_methods"]


def test_task14_conversion_coverage_and_provisional_month():
    """Task 14: Report held-out coverage (81-96%) in meta, and flag provisional month low-count."""
    # 1. Coverage in monthly history meta
    m_resp = get_monthly_history(region_id="india", series="harmonized")
    assert m_resp["meta"].coverage == "81-96% held-out"

    # 2. Coverage in yearly history meta
    y_resp = get_yearly_history(region_id="india", series="harmonized")
    assert y_resp["meta"].coverage == "81-96% held-out"

    # 3. Provisional low-count month (Aug 2026 has 965 detections < 5,000)
    aug_cvm = get_current_vs_median(region_id="india", year=2026, month=8)
    assert aug_cvm["data"].is_provisional is True
    assert aug_cvm["data"].current < 5000
    assert aug_cvm["data"].reliability == "low"
    assert "provisional NRT vs standard-processing baseline; not validated" in aug_cvm["meta"].warnings

