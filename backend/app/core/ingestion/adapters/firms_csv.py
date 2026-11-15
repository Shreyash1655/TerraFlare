"""FIRMS CSV ingestion adapter for MODIS and VIIRS active-fire products."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from app.core.ingestion.base import BaseAdapter
from app.shared.canonical import CANONICAL_COLUMNS, empty_canonical_frame

# Required raw columns that must exist in every FIRMS CSV
REQUIRED_FIRMS_COLUMNS = ["latitude", "longitude", "acq_date", "acq_time", "satellite"]

# Default platform mapping fallback
DEFAULT_PLATFORM_MAP = {
    "Terra": "Terra",
    "Aqua": "Aqua",
    "T": "Terra",
    "A": "Aqua",
    "SNPP": "S-NPP",
    "Suomi-NPP": "S-NPP",
    "NPP": "S-NPP",
    "N20": "NOAA-20",
    "NOAA-20": "NOAA-20",
    "J1": "NOAA-20",
    "N21": "NOAA-21",
    "NOAA-21": "NOAA-21",
    "J2": "NOAA-21",
}


def determine_stream(
    source_file: str | None,
    stream_patterns: dict[str, str] | None = None,
    default: str = "SP",
) -> str:
    """Determine processing stream (SP vs NRT) per file using filename patterns.

    Default patterns:
      SP:  *fire_archive_*.csv
      NRT: *fire_nrt_*.csv
    """
    if not source_file:
        return default

    filename = Path(source_file).name.lower()
    patterns = stream_patterns or {
        "SP": "*fire_archive_*.csv",
        "NRT": "*fire_nrt_*.csv",
    }

    for stream_name, pattern in patterns.items():
        if fnmatch.fnmatch(filename, pattern.lower()):
            return stream_name

    # Fallback substring checks
    if "nrt" in filename:
        return "NRT"
    if "archive" in filename:
        return "SP"
    return default


def count_file_lines(path: Path) -> int:
    """Quickly count total lines in a file using a large binary buffer."""
    count = 0
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            count += chunk.count(b"\n")
    return count


def pad_acq_time(val: Any) -> str:
    """Pad acquisition time to 4 digits (HHMM).

    Examples:
        134 -> "0134"
        0 -> "0000"
        501 -> "0501"
        "1230" -> "1230"
    """
    if pd.isna(val) or val is None:
        return "0000"
    s = str(val).strip().split(".")[0]
    digits = "".join(filter(str.isdigit, s))
    if not digits:
        return "0000"
    return digits.zfill(4)[-4:]


class FirmsCSVAdapter(BaseAdapter):
    """Adapter for FIRMS (Fire Information for Resource Management System) CSV files."""

    adapter_name: str = "firms_csv"

    def __init__(self, source_cfg: dict[str, Any] | None = None) -> None:
        super().__init__(source_cfg)
        self.chunksize = self.source_cfg.get("chunksize", 50000)

    def read(
        self,
        path: Path | str,
        nrows: int | None = None,
        sample_mode: str = "first",
        year: int | str | list[str | int] | None = None,
    ) -> pd.DataFrame:
        """Read a raw FIRMS CSV file, handling large files efficiently.

        Args:
            path: Path to the CSV file.
            nrows: If specified, read up to `nrows` rows (useful for fast sampling).
            sample_mode: 'first' takes first N rows; 'spread' takes every k-th row across the file.
            year: Optional year or list of years to filter on chunk-by-chunk during reading.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        if nrows is not None:
            if sample_mode == "spread":
                total_lines = count_file_lines(p)
                data_rows = max(0, total_lines - 1)
                if data_rows <= nrows or nrows <= 0:
                    df = pd.read_csv(p, dtype=str, keep_default_na=False, nrows=nrows)
                else:
                    step = max(1, data_rows // nrows)
                    df = pd.read_csv(
                        p,
                        dtype=str,
                        keep_default_na=False,
                        skiprows=lambda i: i > 0 and (i - 1) % step != 0,
                        nrows=nrows,
                    )
            else:
                df = pd.read_csv(p, dtype=str, keep_default_na=False, nrows=nrows)

            if year is not None and not df.empty:
                years_str = [str(y) for y in year] if isinstance(year, (list, tuple, set)) else [str(year)]
                pat = "|".join(f"^{y}" for y in years_str)
                for col in ["acq_date", "date"]:
                    if col in df.columns:
                        df = df[df[col].astype(str).str.contains(pat, regex=True)]
                        break
            return df

        # If file is larger than 10MB, read in chunks and filter chunk-by-chunk
        if p.stat().st_size > 10 * 1024 * 1024:
            chunks: list[pd.DataFrame] = []
            years_str = (
                [str(y) for y in year] if isinstance(year, (list, tuple, set)) else ([str(year)] if year else None)
            )
            pat = "|".join(f"^{y}" for y in years_str) if years_str else None

            for chunk in self.read_chunks(p, chunksize=self.chunksize):
                if pat:
                    for col in ["acq_date", "date"]:
                        if col in chunk.columns:
                            chunk = chunk[chunk[col].astype(str).str.contains(pat, regex=True)]
                            break
                if not chunk.empty:
                    chunks.append(chunk)

            if not chunks:
                return pd.DataFrame()
            return pd.concat(chunks, ignore_index=True)

        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        if year is not None and not df.empty:
            years_str = [str(y) for y in year] if isinstance(year, (list, tuple, set)) else [str(year)]
            pat = "|".join(f"^{y}" for y in years_str)
            for col in ["acq_date", "date"]:
                if col in df.columns:
                    df = df[df[col].astype(str).str.contains(pat, regex=True)]
                    break
        return df

    def read_chunks(self, path: Path | str, chunksize: int = 50000) -> Iterator[pd.DataFrame]:
        """Generator yielding raw DataFrame chunks from a CSV file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        for chunk in pd.read_csv(p, dtype=str, chunksize=chunksize, keep_default_na=False):
            yield chunk

    def to_canonical(
        self,
        raw: pd.DataFrame,
        batch_id: str | None = None,
        source_file: str | None = None,
        processing_stream: str | None = None,
    ) -> pd.DataFrame:
        """Convert raw FIRMS DataFrame to canonical schema DataFrame.

        Validates presence of required columns, pads acquisition time,
        maps satellite to platform, determines processing_stream per file,
        keeps raw confidence and fire_type, places unmapped columns in extras,
        and computes stable obs_id.
        """
        if raw.empty:
            return empty_canonical_frame()

        # 1. Validate required columns
        missing = [col for col in REQUIRED_FIRMS_COLUMNS if col not in raw.columns]
        if missing:
            raise ValueError(
                f"Missing required column(s) in FIRMS CSV for source '{self.source_id}': "
                f"{sorted(missing)}. Found columns: {list(raw.columns)}"
            )

        n_rows = len(raw)
        batch = batch_id or f"batch_{self.source_id}"

        # 2. Determine processing stream per file from stream_patterns
        patterns = self.source_cfg.get("stream_patterns")
        stream = (
            processing_stream
            if processing_stream is not None
            else determine_stream(source_file, stream_patterns=patterns, default=self.processing_stream)
        )

        # 3. Coordinates
        lat_series = pd.to_numeric(raw["latitude"], errors="coerce")
        lon_series = pd.to_numeric(raw["longitude"], errors="coerce")

        # 4. Acquisition date and time parsing
        date_str = raw["acq_date"].astype(str).str.strip()
        time_padded = raw["acq_time"].apply(pad_acq_time)

        # Parse date and datetime (UTC)
        acq_date = pd.to_datetime(date_str, errors="coerce").dt.date
        dt_strings = date_str + " " + time_padded.str[:2] + ":" + time_padded.str[2:] + ":00"
        acq_datetime_utc = pd.to_datetime(dt_strings, utc=True, errors="coerce")

        # 5. Satellite & Platform mapping
        sat_raw = raw["satellite"].astype(str).str.strip()
        plat_map = {**DEFAULT_PLATFORM_MAP, **self.platform_map}
        platform = sat_raw.map(plat_map)
        # Fallback for unmapped platforms
        if platform.isna().any():
            platform = platform.fillna(sat_raw)

        # 6. Instrument & confidence
        inst_raw = raw["instrument"].astype(str).str.strip() if "instrument" in raw.columns else None
        conf_raw = raw["confidence"].astype(str).str.strip() if "confidence" in raw.columns else None

        # 7. FRP
        frp_mw = pd.to_numeric(raw["frp"], errors="coerce") if "frp" in raw.columns else None

        # 8. Day/Night
        day_night = raw["daynight"].astype(str).str.strip() if "daynight" in raw.columns else None

        # 9. Type -> fire_type
        fire_type = raw["type"].astype(str).str.strip() if "type" in raw.columns else None

        # 10. Extras (unmapped columns)
        mapped_cols = {
            "latitude", "longitude", "acq_date", "acq_time",
            "satellite", "instrument", "confidence", "frp", "daynight", "type",
        }
        unmapped_cols = [c for c in raw.columns if c not in mapped_cols]
        if unmapped_cols:
            records = raw[unmapped_cols].to_dict("records")
            extras_series = pd.Series(
                [
                    json.dumps({k: v for k, v in r.items() if v != "" and not pd.isna(v)})
                    for r in records
                ],
                index=raw.index,
            )
        else:
            extras_series = pd.Series([None] * n_rows, index=raw.index)

        # 11. Stable obs_id
        # Hash of source_id, platform, lat, lon, acq_date and acq_time
        obs_ids = [
            hashlib.sha256(
                f"{self.source_id}|{p}|{la:.5f}|{lo:.5f}|{d}|{t}".encode("utf-8")
            ).hexdigest()
            for p, la, lo, d, t in zip(platform, lat_series, lon_series, date_str, time_padded)
        ]

        # 12. Build canonical DataFrame
        df_out = pd.DataFrame(index=raw.index)
        df_out["obs_id"] = obs_ids
        df_out["source_id"] = self.source_id
        df_out["sensor_family"] = self.sensor_family
        df_out["platform"] = platform
        df_out["processing_stream"] = stream
        df_out["product_version"] = self.product_version
        df_out["ingest_batch_id"] = batch
        df_out["acq_date"] = pd.to_datetime(acq_date)
        df_out["lat"] = lat_series
        df_out["lon"] = lon_series
        df_out["is_valid"] = True
        df_out["qc_flags"] = "[]"
        df_out["is_synthetic"] = bool(self.source_cfg.get("is_synthetic", False))

        # Optional fields
        df_out["acq_datetime_utc"] = acq_datetime_utc
        df_out["local_date"] = pd.NaT
        df_out["h3_cell"] = None
        df_out["confidence_raw"] = conf_raw
        df_out["confidence_class"] = None  # Normalized during cleaning stage
        df_out["frp_mw"] = frp_mw
        df_out["day_night"] = day_night
        df_out["fire_type"] = fire_type
        df_out["satellite_raw"] = sat_raw
        df_out["instrument_raw"] = inst_raw
        df_out["extras"] = extras_series

        # Reorder to match CANONICAL_COLUMNS
        for col in CANONICAL_COLUMNS:
            if col not in df_out.columns:
                df_out[col] = None

        return df_out[CANONICAL_COLUMNS]

