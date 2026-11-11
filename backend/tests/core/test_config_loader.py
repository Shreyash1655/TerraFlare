"""Tests for app/shared/config_loader.py – YAML config loading."""

from __future__ import annotations

import pytest

from app.shared.config_loader import (
    get_harmonization_config,
    get_regions_config,
    get_sources,
    load_yaml_config,
)


class TestLoadYamlConfig:
    def test_nonexistent_file_returns_empty_dict(self):
        result = load_yaml_config("does_not_exist_xyz.yaml")
        assert result == {}

    def test_sources_yaml_loads(self):
        cfg = load_yaml_config("sources.yaml")
        assert isinstance(cfg, dict)
        assert "sources" in cfg

    def test_harmonization_yaml_loads(self):
        cfg = load_yaml_config("harmonization.yaml")
        assert isinstance(cfg, dict)
        assert "harmonization" in cfg

    def test_regions_yaml_loads(self):
        cfg = load_yaml_config("regions.yaml")
        assert isinstance(cfg, dict)
        assert "regions" in cfg


class TestGetSources:
    def test_returns_dict(self):
        sources = get_sources()
        assert isinstance(sources, dict)

    def test_all_four_sources_present(self):
        sources = get_sources()
        for key in ("modis_c61", "viirs_snpp", "viirs_noaa20", "viirs_noaa21"):
            assert key in sources, f"Missing source: {key}"

    def test_modis_sensor_family(self):
        assert get_sources()["modis_c61"]["sensor_family"] == "MODIS"

    def test_viirs_sensor_families(self):
        for key in ("viirs_snpp", "viirs_noaa20", "viirs_noaa21"):
            assert get_sources()[key]["sensor_family"] == "VIIRS"

    def test_modis_adapter(self):
        assert get_sources()["modis_c61"]["adapter"] == "firms_csv"

    def test_all_sources_have_field_map(self):
        for key, src in get_sources().items():
            assert "field_map" in src, f"{key} missing field_map"

    def test_all_sources_have_confidence_map(self):
        for key, src in get_sources().items():
            assert "confidence_map" in src, f"{key} missing confidence_map"

    def test_all_sources_have_platform_map(self):
        for key, src in get_sources().items():
            assert "platform_map" in src, f"{key} missing platform_map"


class TestGetHarmonizationConfig:
    def test_returns_dict(self):
        cfg = get_harmonization_config()
        assert isinstance(cfg, dict)

    def test_h3_resolution_is_6(self):
        assert get_harmonization_config()["h3_resolution"] == 6

    def test_reference_sensor_is_viirs(self):
        assert get_harmonization_config()["reference_sensor"] == "VIIRS"

    def test_local_date_rule_is_solar(self):
        assert get_harmonization_config()["local_date_rule"] == "solar"

    def test_enabled_methods_present(self):
        methods = get_harmonization_config()["enabled_methods"]
        assert "identity" in methods
        assert "stratified_ratio" in methods

    def test_bootstrap_config(self):
        bs = get_harmonization_config()["bootstrap"]
        assert bs["block_days"] == 7
        assert bs["reps"] == 500
        assert bs["interval_level"] == pytest.approx(0.9)

    def test_provisional_months(self):
        assert get_harmonization_config()["provisional_months"] == 5

    def test_min_confidence_class(self):
        assert get_harmonization_config()["min_confidence_class"] == "nominal"


class TestGetRegionsConfig:
    def test_returns_dict(self):
        cfg = get_regions_config()
        assert isinstance(cfg, dict)

    def test_india_present(self):
        assert "india" in get_regions_config()

