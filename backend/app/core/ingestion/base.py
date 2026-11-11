"""Abstract base class for all TerraFlare source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

import pandas as pd


class BaseAdapter(ABC):
    """All ingestion adapters must implement this interface."""

    adapter_name: str = "base"

    def __init__(self, source_cfg: dict[str, Any] | None = None) -> None:
        self.source_cfg = source_cfg or {}
        self.source_id = self.source_cfg.get("source_id", "unknown")
        self.sensor_family = self.source_cfg.get("sensor_family", "UNKNOWN")
        self.product_version = self.source_cfg.get("product_version", "unknown")
        self.processing_stream = self.source_cfg.get("processing_stream", "SP")
        self.platform_map = self.source_cfg.get("platform_map", {})
        self.field_map = self.source_cfg.get("field_map", {})

    @abstractmethod
    def read(self, path: Path | str, **kwargs: Any) -> pd.DataFrame:
        """Read raw source file and return a raw DataFrame."""

    @abstractmethod
    def to_canonical(
        self,
        raw: pd.DataFrame,
        batch_id: str | None = None,
        source_file: str | None = None,
    ) -> pd.DataFrame:
        """Convert raw source DataFrame to canonical DataFrame."""
