"""Cleaning and normalisation package for TerraFlare."""

from app.core.cleaning.normalize import (
    compute_solar_local_date,
    normalize_canonical_dataframe,
    normalize_confidence_modis,
    normalize_confidence_viirs,
)
from app.core.cleaning.report import (
    build_cleaning_report,
    clean_observations,
    format_cleaning_report,
    print_cleaning_report,
    save_cleaning_report,
)
from app.core.cleaning.rules import (
    apply_cleaning_rules,
    check_coordinate_range,
    check_duplicate_obs_id,
    check_missing_date,
    check_negative_frp,
    filter_confidence,
    filter_fire_type,
)

__all__ = [
    "compute_solar_local_date",
    "normalize_canonical_dataframe",
    "normalize_confidence_modis",
    "normalize_confidence_viirs",
    "check_coordinate_range",
    "check_missing_date",
    "check_duplicate_obs_id",
    "filter_fire_type",
    "filter_confidence",
    "check_negative_frp",
    "apply_cleaning_rules",
    "build_cleaning_report",
    "save_cleaning_report",
    "format_cleaning_report",
    "print_cleaning_report",
    "clean_observations",
]
