"""Read-only access to the harmonized datasets (Member 1's parquet files, or synthetic fixture)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.utils.errors import TerraFlareError
from app.utils.fixture_data import build_fixture

HARMONIZED_OPTIONAL = ["harmonized_lower", "harmonized_upper", "modis_observed", "viirs_observed"]


class DataRepository:
    def __init__(self, data_dir: Path, mode: str = "auto", default_version: str = "dev-0"):
        self.data_dir = Path(data_dir)
        real_exists = (self.data_dir / "harmonized_cell_day.parquet").exists()
        if mode == "real" and not real_exists:
            raise RuntimeError(f"TERRAFLARE_DATA_MODE=real but {self.data_dir}/harmonized_cell_day.parquet is missing")
        self.mode = "real" if (mode == "real" or (mode == "auto" and real_exists)) else "fixture"
        self._tables: dict[str, pd.DataFrame | None] = {}
        self._fixture: dict | None = None
        self.data_version = "fixture-0" if self.mode == "fixture" else self._read_manifest_version(default_version)

    # ------------------------------------------------------------------ meta
    @property
    def is_synthetic(self) -> bool:
        return self.mode == "fixture"

    @property
    def method_id(self) -> str | None:
        return self.get_calibration_info().get("method_id")

    def _read_manifest_version(self, default: str) -> str:
        for p in (self.data_dir / "manifest.json", self.data_dir.parent / "manifest.json"):
            if p.exists():
                try:
                    return str(json.loads(p.read_text()).get("data_version", default))
                except (ValueError, OSError):
                    pass
        return default

    # --------------------------------------------------------------- loading
    def _fx(self) -> dict:
        if self._fixture is None:
            self._fixture = build_fixture()
        return self._fixture

    def _table(self, name: str) -> pd.DataFrame | None:
        if name in self._tables:
            return self._tables[name]
        if self.mode == "fixture":
            df = self._fx().get(name)
        else:
            p = self.data_dir / f"{name}.parquet"
            df = pd.read_parquet(p) if p.exists() else None
        if df is not None:
            df = df.copy()
            if "acq_date" in df.columns:
                df["acq_date"] = pd.to_datetime(df["acq_date"]).dt.normalize()
            if name == "harmonized_cell_day":
                for c in HARMONIZED_OPTIONAL:
                    if c not in df.columns:
                        df[c] = np.nan
        self._tables[name] = df
        return df

    def _require(self, name: str) -> pd.DataFrame:
        df = self._table(name)
        if df is None:
            raise TerraFlareError(
                "dataset_unavailable", f"Dataset '{name}' is not available", 503, {"dataset": name}
            )
        return df

    @staticmethod
    def _filter(df: pd.DataFrame, region_id, start, end) -> pd.DataFrame:
        if region_id and "region_id" in df.columns:
            if region_id not in set(df["region_id"].unique()):
                raise TerraFlareError("region_not_found", f"Unknown region_id '{region_id}'", 404)
            df = df[df["region_id"] == region_id]
        if start is not None:
            df = df[df["acq_date"] >= pd.Timestamp(start)]
        if end is not None:
            df = df[df["acq_date"] <= pd.Timestamp(end)]
        return df

    # ------------------------------------------------------------ public API
    def get_harmonized(self, region_id=None, start=None, end=None, series="harmonized") -> pd.DataFrame:
        """harmonized_cell_day. Treat the result as read-only."""
        df = self._filter(self._require("harmonized_cell_day"), region_id, start, end)
        if not df.empty and series != "harmonized":
            df = df.copy()
            if series == "viirs_native":
                df = df[df["acq_date"] >= "2012-01-01"].copy()
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

    def get_observations(self, region_id=None, start=None, end=None, sensors=None, valid_only=True) -> pd.DataFrame:
        """obs_clean (point-level)."""
        df = self._filter(self._require("obs_clean"), region_id, start, end)
        if valid_only and "is_valid" in df.columns:
            df = df[df["is_valid"].fillna(False)]
        if sensors:
            df = df[df["sensor_family"].str.upper().isin([s.upper() for s in sensors])]
        return df

    def get_provenance(self) -> pd.DataFrame:
        df = self._table("ingest_log")
        return df if df is not None else pd.DataFrame()

    def get_calibration_info(self) -> dict:
        if self.mode == "fixture":
            return self._fx()["calibration_info"]
        info: dict = {"method_id": None, "validation": []}
        h = self._table("harmonized_cell_day")
        if h is not None and "method_id" in h.columns and h["method_id"].notna().any():
            info["method_id"] = str(h["method_id"].mode().iloc[0])
        v = self._table("validation_results")
        if v is not None:
            cols = [c for c in ["metric_name", "value", "ci_lower", "ci_upper", "baseline_id"] if c in v.columns]
            info["validation"] = v[cols].astype(object).where(v[cols].notna(), None).to_dict("records")
        return info

    def data_range(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        h = self._require("harmonized_cell_day")
        if h.empty:
            raise TerraFlareError("no_data", "harmonized_cell_day is empty", 404)
        return h["acq_date"].min(), h["acq_date"].max()

    def get_layers(self) -> dict[str, dict]:
        """External exposure layers: {layer_id: {df(lat, lon, [value]), source, version, is_synthetic}}."""
        if self.mode == "fixture":
            return self._fx()["layers"]
        out: dict[str, dict] = {}
        for p in sorted((self.data_dir / "layers").glob("*.parquet")):
            meta: dict = {}
            side = p.with_suffix(".json")
            if side.exists():
                meta = json.loads(side.read_text())
            out[p.stem] = {
                "df": pd.read_parquet(p),
                "source": meta.get("source"),
                "version": meta.get("version"),
                "is_synthetic": bool(meta.get("is_synthetic", False)),
            }
        return out