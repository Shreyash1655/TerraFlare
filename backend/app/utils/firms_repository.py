"""Opt-in repository serving real FIRMS NRT obs_clean / ingest_log. The synthetic fixture is never served in this mode."""
import numpy as np
import pandas as pd
from app.utils.data_repository import DataRepository

FIRMS_TABLES = {"obs_clean", "ingest_log"}
HARMONIZED_COLS = ["acq_date", "region_id", "h3_cell", "harmonized_value", "harmonized_lower", "harmonized_upper",
                   "modis_observed", "viirs_observed", "interval_level", "method_id"]


class FirmsNrtRepository(DataRepository):
    obs_source = "firms_nrt"

    def __init__(self, data_dir, mode="auto", default_version="dev-0"):
        super().__init__(data_dir, "fixture", default_version)  # never raises, whatever TERRAFLARE_DATA_MODE is
        self.mode = "firms_nrt"          # is_synthetic -> False; non-FIRMS tables are NOT taken from the fixture
        self.data_version = self._firms_version(default_version)
        self._range_cache = None

    def _firms_version(self, default: str) -> str:
        p = self.data_dir / "firms" / "ingest_log.parquet"
        try:
            t = pd.read_parquet(p, columns=["t_max"])["t_max"].max()
            return f"firms-nrt-{str(t)[:10]}"
        except Exception:
            return default

    def _table(self, name: str):
        if name in FIRMS_TABLES and name not in self._tables:
            p = self.data_dir / "firms" / f"{name}.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                if "acq_date" in df.columns:
                    df["acq_date"] = pd.to_datetime(df["acq_date"]).dt.normalize()
                self._tables[name] = df
            else:
                self._tables[name] = None
        return super()._table(name)

    def data_range(self):
        """Real range of obs_clean (acq_date), so events/exposure/quality see every loaded day."""
        if self._range_cache is None:
            df = self._table("obs_clean")
            if df is not None and len(df) and "acq_date" in df.columns:
                d = pd.to_datetime(df["acq_date"]).dropna()
                if len(d):
                    self._range_cache = (d.min().normalize(), d.max().normalize())
        return self._range_cache if self._range_cache is not None else super().data_range()

    def get_harmonized(self, region_id=None, start=None, end=None):
        """No cross-sensor harmonized product exists for NRT data: return an empty frame, never fixture data."""
        return pd.DataFrame({c: pd.Series(dtype="float64" if c not in ("region_id", "h3_cell", "method_id") else "object")
                             for c in HARMONIZED_COLS}).astype({"acq_date": "datetime64[ns]"})