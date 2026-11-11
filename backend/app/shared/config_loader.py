"""Central YAML configuration loader for TerraFlare.

Usage
-----
    from app.shared.config_loader import load_yaml_config
    sources = load_yaml_config("sources.yaml")
    regions = load_yaml_config("regions.yaml")

All thresholds and parameters live in config/*.yaml.
Nothing is hard-coded in service or analytics modules.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Resolve the config/ directory relative to the repo root.
# backend/app/shared/config_loader.py -> parents[3] = repo root -> config/
_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def load_yaml_config(filename: str) -> dict[str, Any]:
    """Load and return a YAML config file from the config/ directory.

    Args:
        filename: Bare filename, e.g. ``"sources.yaml"``.

    Returns:
        Parsed YAML as a dict. Returns ``{}`` if the file does not exist.

    Raises:
        yaml.YAMLError: If the file exists but is not valid YAML.
    """
    path = _CONFIG_DIR / filename
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=16)
def _cached_load(filename: str) -> dict[str, Any]:
    """Cached version – used for configs that never change at runtime."""
    return load_yaml_config(filename)


def get_sources() -> dict[str, Any]:
    """Return the sources config (cached after first load)."""
    return _cached_load("sources.yaml").get("sources", {})


def get_harmonization_config() -> dict[str, Any]:
    """Return the harmonization config (cached after first load)."""
    return _cached_load("harmonization.yaml").get("harmonization", {})


def get_regions_config() -> dict[str, Any]:
    """Return the regions config (cached after first load)."""
    return _cached_load("regions.yaml").get("regions", {})

