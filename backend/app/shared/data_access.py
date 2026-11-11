"""Read-only access layer and Protocol for TerraFlare datasets."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataRepository(Protocol):
    """Formal protocol for reading harmonised datasets and observation marts."""

    # obs_clean (point-level canonical observations)
    def get_observations(
        self,
        region_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        sensors: list[str] | None = None,
        valid_only: bool = True,
    ) -> pd.DataFrame: ...

    # cell_day_activity (per sensor, per cell, per day)
    def get_cell_day(
        self,
        region_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        sensors: list[str] | None = None,
    ) -> pd.DataFrame: ...

    # harmonized_cell_day (THE common harmonized dataset)
    def get_harmonized(
        self,
        region_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        series: str = "harmonized",
    ) -> pd.DataFrame: ...

    # monthly_activity
    def get_monthly(
        self,
        region_id: str | None = None,
    ) -> pd.DataFrame: ...

    # ingest_log + versions
    def get_provenance(self) -> pd.DataFrame: ...

    # method, fit period, validation summary
    def get_calibration_info(self) -> dict[str, Any]: ...

    # which optional fields and features exist
    def get_capabilities(self) -> dict[str, Any]: ...


from app.core.storage.duckdb_repo import DuckDBRepository

__all__ = ["DataRepository", "DuckDBRepository"]
