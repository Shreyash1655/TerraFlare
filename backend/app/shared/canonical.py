"""Canonical observation schema for TerraFlare.

Every row that passes the ingestion adapters must conform to this schema
before entering the cleaning → spatial → harmonisation pipeline.

Design decisions
----------------
* Required fields are populated by the adapter at read time.
* h3_cell, local_date, acq_datetime_utc are OPTIONAL – the spatial and
  temporal enrichment steps fill them later in the pipeline.
* confidence_raw is always a *string* so both MODIS (0–100 integer) and
  VIIRS (low/nominal/high) values can be stored without loss.
* confidence_class is normalised per-sensor during the cleaning step;
  it is not set by adapters.
* extras holds unmapped source columns as a JSON string; never drop them
  silently – the cleaning report must account for every field.
* Never add MODIS and VIIRS FRP or counts together; keep sensor_family
  and platform on every row.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Column registry
# ---------------------------------------------------------------------------

# (column_name, numpy dtype)  – used to build the empty canonical DataFrame.
# "object" dtype is used for string/JSON columns so pandas stores them as str.
_COLUMN_DTYPES: list[tuple[str, str]] = [
    # -- required ----------------------------------------------------------
    ("obs_id",            "object"),    # unique observation identifier
    ("source_id",         "object"),    # adapter source key, e.g. "modis_c61"
    ("sensor_family",     "object"),    # "MODIS" or "VIIRS"
    ("platform",          "object"),    # "Terra", "Aqua", "S-NPP", "NOAA-20", "NOAA-21"
    ("processing_stream", "object"),    # "NRT" or "SP"
    ("product_version",   "object"),    # e.g. "Collection 6.1"
    ("ingest_batch_id",   "object"),    # UUID / slug set by ingest orchestrator
    ("acq_date",          "datetime64[ns]"),
    ("lat",               "float64"),
    ("lon",               "float64"),
    ("is_valid",          "bool"),
    ("qc_flags",          "object"),    # JSON array string of flag names
    ("is_synthetic",      "bool"),
    # -- optional (filled later in pipeline) --------------------------------
    ("acq_datetime_utc",  "datetime64[ns]"),
    ("local_date",        "datetime64[ns]"),
    ("h3_cell",           "object"),    # H3 index string – filled by spatial step
    ("confidence_raw",    "object"),    # raw string: "72" or "nominal" etc.
    ("confidence_class",  "object"),    # "low", "nominal", "high", "unknown"
    ("frp_mw",            "float64"),
    ("day_night",         "object"),    # "D" or "N"
    ("fire_type",         "object"),    # e.g. "presumed vegetation fire"
    ("satellite_raw",     "object"),    # raw satellite value from source CSV
    ("instrument_raw",    "object"),    # raw instrument field from source CSV
    ("static_masked",     "bool"),      # True if flagged as static source (archive type 2/3 or NRT in static mask)
    ("extras",            "object"),    # JSON string – unmapped source columns
]

CANONICAL_COLUMNS: list[str] = [col for col, _ in _COLUMN_DTYPES]
dtypes: dict[str, str] = dict(_COLUMN_DTYPES)
CANONICAL_DTYPES: dict[str, str] = dtypes


def _canonical_dtypes() -> dict[str, str]:
    """Return column → numpy dtype mapping for the canonical schema."""
    return dtypes


def empty_canonical_frame() -> pd.DataFrame:
    """Return an empty DataFrame with canonical columns and correct dtypes.

    Use this as the target schema when building or validating DataFrames
    at any pipeline stage.
    """
    dtypes = _canonical_dtypes()
    df = pd.DataFrame(columns=CANONICAL_COLUMNS)
    for col, dtype in dtypes.items():
        if dtype == "bool":
            # Nullable boolean; bool columns in an empty frame cause issues
            # with concat unless we use object first, then cast on data arrival.
            df[col] = pd.array([], dtype=pd.BooleanDtype())
        elif dtype.startswith("datetime"):
            df[col] = pd.array([], dtype="datetime64[ns]")
        else:
            df[col] = pd.array([], dtype=dtype)
    return df


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------

_SENSOR_FAMILIES = Literal["MODIS", "VIIRS"]
_PLATFORMS = Literal["Terra", "Aqua", "S-NPP", "NOAA-20", "NOAA-21"]
_PROCESSING_STREAMS = Literal["NRT", "SP"]
_CONFIDENCE_CLASSES = Literal["low", "nominal", "high", "unknown"]
_DAY_NIGHT = Literal["D", "N"]


class CanonicalObservation(BaseModel):
    """One cleaned, pre-harmonisation fire detection row.

    Instantiate this model to validate a single observation dictionary
    before writing it to the canonical DataFrame layer.
    """

    # ---- required --------------------------------------------------------
    obs_id: str = Field(..., description="Unique observation identifier")
    source_id: str = Field(..., description="Adapter source key, e.g. 'modis_c61'")
    sensor_family: _SENSOR_FAMILIES = Field(..., description="Sensor family: MODIS or VIIRS")
    platform: _PLATFORMS = Field(
        ..., description="Controlled-vocabulary platform name"
    )
    processing_stream: _PROCESSING_STREAMS = Field(
        ..., description="'NRT' for near-real-time, 'SP' for standard/archive product"
    )
    product_version: str = Field(..., description="Source product version, e.g. 'Collection 6.1'")
    ingest_batch_id: str = Field(
        ..., description="Batch UUID/slug assigned by the ingest orchestrator"
    )
    acq_date: date = Field(..., description="Acquisition date in UTC")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude WGS-84")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude WGS-84")
    is_valid: bool = Field(True, description="False when the row is flagged by a cleaning rule")
    qc_flags: list[str] | str = Field(
        "[]", description="JSON array string or list of QC flag names applied to this row"
    )
    is_synthetic: bool = Field(
        False,
        description="True for fixture/test data only. Never True for real NASA observations.",
    )

    # ---- optional (populated by pipeline steps after ingestion) ----------
    acq_datetime_utc: datetime | None = Field(
        None, description="Exact UTC acquisition datetime – filled by temporal enrichment"
    )
    local_date: date | None = Field(
        None, description="Acquisition date in local solar time – filled by temporal enrichment"
    )
    h3_cell: str | None = Field(
        None,
        description="H3 hexagonal cell index – filled by spatial enrichment step, NOT at ingestion",
    )
    confidence_raw: str | None = Field(
        None,
        description=(
            "Raw confidence value as a string: an integer 0–100 for MODIS, "
            "or 'low'/'nominal'/'high' for VIIRS"
        ),
    )
    confidence_class: _CONFIDENCE_CLASSES | None = Field(
        None,
        description="Normalised confidence class – set per-sensor during cleaning, not by adapters",
    )
    frp_mw: float | None = Field(
        None, ge=0.0, description="Fire Radiative Power in megawatts"
    )
    day_night: _DAY_NIGHT | None = Field(None, description="'D' (day) or 'N' (night) overpass")
    fire_type: str | None = Field(
        None, description="Fire type as reported by source, e.g. 'presumed vegetation fire'"
    )
    satellite_raw: str | None = Field(
        None, description="Raw satellite identifier from the source CSV before platform mapping"
    )
    instrument_raw: str | None = Field(
        None, description="Raw instrument field from the source CSV"
    )
    static_masked: bool | None = Field(
        False, description="True if flagged as static source (archive type 2/3 or NRT in static mask)"
    )
    extras: str | None = Field(
        None,
        description=(
            "JSON string of unmapped source columns. "
            "Never drop columns silently – store them here."
        ),
    )

    @field_validator("lat")
    @classmethod
    def _check_lat(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"lat must be in [-90, 90], got {v}")
        return v

    @field_validator("lon")
    @classmethod
    def _check_lon(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"lon must be in [-180, 180], got {v}")
        return v
