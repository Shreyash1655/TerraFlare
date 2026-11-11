"""Tests for app/shared/regions.py and config/regions.yaml."""

from __future__ import annotations

import pytest

from app.shared.regions import (
    BBox,
    Region,
    get_bbox,
    get_region,
    list_region_ids,
    load_regions,
    point_in_region,
)


# ---------------------------------------------------------------------------
# BBox unit tests
# ---------------------------------------------------------------------------

class TestBBox:
    def test_contains_centre_point(self):
        bb = BBox(min_lon=68.0, min_lat=6.0, max_lon=98.0, max_lat=37.0)
        # Centre of India bbox
        assert bb.contains(lat=20.0, lon=80.0)

    def test_contains_boundary_point(self):
        bb = BBox(min_lon=68.0, min_lat=6.0, max_lon=98.0, max_lat=37.0)
        assert bb.contains(lat=6.0, lon=68.0)   # SW corner
        assert bb.contains(lat=37.0, lon=98.0)  # NE corner

    def test_does_not_contain_outside(self):
        bb = BBox(min_lon=68.0, min_lat=6.0, max_lon=98.0, max_lat=37.0)
        assert not bb.contains(lat=5.0, lon=80.0)   # south of bbox
        assert not bb.contains(lat=20.0, lon=67.9)  # west of bbox
        assert not bb.contains(lat=38.0, lon=80.0)  # north of bbox
        assert not bb.contains(lat=20.0, lon=98.1)  # east of bbox

    def test_as_list(self):
        bb = BBox(68.0, 6.0, 98.0, 37.0)
        assert bb.as_list() == [68.0, 6.0, 98.0, 37.0]

    def test_property_aliases(self):
        bb = BBox(68.0, 6.0, 98.0, 37.0)
        assert bb.west  == bb.min_lon
        assert bb.south == bb.min_lat
        assert bb.east  == bb.max_lon
        assert bb.north == bb.max_lat

    def test_str_representation(self):
        bb = BBox(68.0, 6.0, 98.0, 37.0)
        s = str(bb)
        assert "68.0" in s and "37.0" in s


# ---------------------------------------------------------------------------
# Region loader tests (uses real config/regions.yaml)
# ---------------------------------------------------------------------------

class TestLoadRegions:
    def test_returns_dict(self):
        regions = load_regions()
        assert isinstance(regions, dict)

    def test_india_present(self):
        regions = load_regions()
        assert "india" in regions

    def test_goa_western_ghats_present(self):
        regions = load_regions()
        assert "goa_western_ghats" in regions

    def test_region_type(self):
        regions = load_regions()
        assert isinstance(regions["india"], Region)

    def test_india_bbox_values(self):
        region = load_regions()["india"]
        bb = region.bbox
        assert bb.min_lon == pytest.approx(68.0)
        assert bb.min_lat == pytest.approx(6.0)
        assert bb.max_lon == pytest.approx(98.0)
        assert bb.max_lat == pytest.approx(37.0)

    def test_india_contains_delhi(self):
        region = load_regions()["india"]
        # New Delhi ≈ 28.6°N, 77.2°E
        assert region.contains(lat=28.6, lon=77.2)

    def test_india_does_not_contain_pakistan(self):
        region = load_regions()["india"]
        # Karachi ≈ 24.9°N, 67.1°E – just west of bbox
        assert not region.contains(lat=24.9, lon=67.1)

    def test_goa_bbox_is_smaller_than_india(self):
        india_bb = load_regions()["india"].bbox
        goa_bb = load_regions()["goa_western_ghats"].bbox
        # Goa bbox must fit entirely within India bbox
        assert goa_bb.min_lon >= india_bb.min_lon
        assert goa_bb.min_lat >= india_bb.min_lat
        assert goa_bb.max_lon <= india_bb.max_lon
        assert goa_bb.max_lat <= india_bb.max_lat


class TestHelperFunctions:
    def test_list_region_ids_includes_india(self):
        ids = list_region_ids()
        assert "india" in ids

    def test_get_region_returns_region(self):
        r = get_region("india")
        assert r.region_id == "india"
        assert isinstance(r.bbox, BBox)

    def test_get_region_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown_region"):
            get_region("unknown_region")

    def test_get_bbox_returns_bbox(self):
        bb = get_bbox("india")
        assert isinstance(bb, BBox)

    def test_point_in_region_true(self):
        # Mumbai ≈ 19.1°N, 72.9°E – inside India bbox
        assert point_in_region(lat=19.1, lon=72.9, region_id="india")

    def test_point_in_region_false(self):
        # London – outside India bbox
        assert not point_in_region(lat=51.5, lon=-0.1, region_id="india")

