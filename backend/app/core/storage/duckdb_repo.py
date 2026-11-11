"""DuckDB implementation of DataRepository protocol for TerraFlare."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.core.spatial.grid import bbox_to_cells
from app.core.storage.parquet_io import sync_duckdb_views
from app.settings import settings
from app.shared.canonical import CANONICAL_COLUMNS
from app.shared.config_loader import get_harmonization_config
from app.shared.regions import load_regions


class DuckDBRepository:
    """Fast DuckDB repository querying Parquet files via views."""

    def __init__(
        self,
        data_dir: Path | str | None = None,
        db_path: Path | str | None = None,
        read_only: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else settings.data_dir
        self.db_path = Path(db_path) if db_path else (self.data_dir / "terraflare.duckdb")
        self.read_only = read_only
        self.data_mode = settings.data_mode
        self.data_version = settings.data_version
        self._con: duckdb.DuckDBPyConnection | None = None

    @property
    def con(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            self._con = sync_duckdb_views(self.data_dir, self.db_path, read_only=True)
        return self._con

    def refresh_views(self) -> None:
        """Refresh DuckDB views after new Parquet files are generated."""
        self._con = sync_duckdb_views(self.data_dir, self.db_path)

    # -----------------------------------------------------------------------
    # Protocol implementation
    # -----------------------------------------------------------------------

    def get_observations(
        self,
        region_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        sensors: list[str] | None = None,
        valid_only: bool = True,
    ) -> pd.DataFrame:
        """Query cleaned point-level observations from obs_clean view."""
        clauses = ["1=1"]

        if valid_only:
            clauses.append("is_valid = true")

        if start:
            clauses.append(f"acq_date >= '{start}'")

        if end:
            clauses.append(f"acq_date <= '{end}'")

        if sensors:
            sensor_list = ", ".join(f"'{s}'" for s in sensors)
            clauses.append(f"sensor_family IN ({sensor_list})")

        if region_id:
            regions = load_regions()
            if region_id in regions:
                bb = regions[region_id].bbox
                clauses.append(
                    f"lat >= {bb.min_lat} AND lat <= {bb.max_lat} AND "
                    f"lon >= {bb.min_lon} AND lon <= {bb.max_lon}"
                )

        where_sql = " AND ".join(clauses)
        query = f"SELECT * FROM obs_clean WHERE {where_sql}"
        try:
            df = self.con.execute(query).df()
            if df.empty:
                return pd.DataFrame(columns=CANONICAL_COLUMNS)
            return df
        except Exception:
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

    def get_cell_day(
        self,
        region_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        sensors: list[str] | None = None,
    ) -> pd.DataFrame:
        """Query aggregated cell_day_activity."""
        clauses = ["1=1"]

        if start:
            clauses.append(f"date >= '{start}'")

        if end:
            clauses.append(f"date <= '{end}'")

        if sensors:
            sensor_list = ", ".join(f"'{s}'" for s in sensors)
            clauses.append(f"sensor_family IN ({sensor_list})")

        if region_id:
            regions = load_regions()
            if region_id in regions:
                bb = regions[region_id].bbox
                cells = bbox_to_cells(bb)
                if cells:
                    # Filter to cells in the bounding box
                    cell_list = ", ".join(f"'{c}'" for c in list(cells)[:5000])
                    clauses.append(f"h3_cell IN ({cell_list})")

        where_sql = " AND ".join(clauses)
        query = f"SELECT * FROM cell_day_activity WHERE {where_sql}"
        try:
            return self.con.execute(query).df()
        except Exception:
            cols = [
                "source_id", "sensor_family", "platform", "h3_cell",
                "date", "day_night", "n_detections", "n_high_conf",
                "frp_sum_mw", "frp_max_mw",
            ]
            return pd.DataFrame(columns=cols)

    def get_harmonized(
        self,
        region_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        series: str = "harmonized",
    ) -> pd.DataFrame:
        """Query harmonized_cell_day (THE common harmonized dataset).

        series:
            - 'harmonized': default calibrated series
            - 'viirs_native': VIIRS reference series from 2012, no MODIS conversion, bridge uncertainty only (+/- 1.84%)
            - 'modis_native': MODIS observed series, no conversion
        """
        clauses = ["1=1"]
        if start:
            clauses.append(f"acq_date >= '{start}'")
        if end:
            clauses.append(f"acq_date <= '{end}'")
        if region_id:
            clauses.append(f"region_id = '{region_id}'")

        if series == "viirs_native":
            clauses.append("acq_date >= '2012-01-01'")

        where_sql = " AND ".join(clauses)
        query = f"SELECT * FROM harmonized_cell_day WHERE {where_sql}"
        try:
            df = self.con.execute(query).df()
            if not df.empty and series != "harmonized":
                if series == "viirs_native":
                    df["harmonized_value"] = df["viirs_observed"].fillna(0.0)
                    df["harmonized_lower"] = (df["harmonized_value"] * (1.0 - 0.0184)).round(4)
                    df["harmonized_upper"] = (df["harmonized_value"] * (1.0 + 0.0184)).round(4)
                    df["value_type"] = "observed"
                    df["method_id"] = "viirs_native"
                elif series == "modis_native":
                    df["harmonized_value"] = df["modis_observed"].fillna(0.0)
                    df["harmonized_lower"] = df["harmonized_value"]
                    df["harmonized_upper"] = df["harmonized_value"]
                    df["value_type"] = "observed"
                    df["method_id"] = "modis_native"
            return df
        except Exception:
            cols = [
                "h3_cell", "acq_date", "region_id", "harmonized_value",
                "harmonized_lower", "harmonized_upper", "modis_observed",
                "viirs_observed", "interval_level", "method_id", "value_type",
            ]
            return pd.DataFrame(columns=cols)

    def get_monthly(
        self,
        region_id: str | None = None,
    ) -> pd.DataFrame:
        """Query monthly_activity."""
        clauses = ["1=1"]
        if region_id:
            clauses.append(f"region_id = '{region_id}'")

        where_sql = " AND ".join(clauses)
        query = f"SELECT * FROM monthly_activity WHERE {where_sql}"
        try:
            return self.con.execute(query).df()
        except Exception:
            cols = [
                "region_id", "year_month", "value_type", "sensor_family",
                "value", "lower", "upper", "data_version",
            ]
            return pd.DataFrame(columns=cols)

    def get_provenance(self) -> pd.DataFrame:
        """Query ingest_log provenance records."""
        try:
            return self.con.execute("SELECT * FROM ingest_log ORDER BY ingested_at DESC").df()
        except Exception:
            cols = ["source_id", "file_name", "sha256", "rows_in", "ingested_at"]
            return pd.DataFrame(columns=cols)

    def get_calibration_info(self) -> dict[str, Any]:
        """Return calibration metadata and method details."""
        try:
            df = self.con.execute("SELECT * FROM calibration_models").df()
            if not df.empty:
                records = df.to_dict(orient="records")
                primary = records[0]
                return {
                    "method_id": primary.get("method_id", "stratified_ratio"),
                    "models": records,
                    "bridge_info": {
                        "min_date": primary.get("bridge_min_date"),
                        "max_date": primary.get("bridge_max_date"),
                        "bridge_ratio": primary.get("bridge_ratio"),
                    },
                    "fitted_at": primary.get("fitted_at"),
                }
        except Exception:
            pass

        return {
            "method_id": "stratified_ratio",
            "fit_period": None,
            "validation_summary": {},
        }

    def get_capabilities(self) -> dict[str, Any]:
        """Return optional fields and features supported by the pipeline."""
        h3_res = int(get_harmonization_config().get("h3_resolution", 6))
        return {
            "sensors": ["MODIS", "VIIRS"],
            "h3_resolution": h3_res,
            "has_frp": True,
            "has_confidence": True,
            "has_day_night": True,
            "has_platform": True,
            "features_enabled": list(settings.enabled_features),
        }

