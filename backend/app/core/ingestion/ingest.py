"""Ingestion pipeline: reads raw sources, writes raw Parquet, ingest_log, and canonical Parquet."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.ingestion import registry
from app.settings import settings
from app.shared.config_loader import get_sources


def compute_file_sha256(path: Path | str) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def resolve_location_pattern(pattern: str, data_dir: Path) -> list[Path]:
    """Resolve location pattern by expanding ${TERRAFLARE_DATA_DIR} and globbing."""
    resolved_str = pattern.replace("${TERRAFLARE_DATA_DIR}", str(data_dir))
    p = Path(resolved_str)
    parent = p.parent

    if not parent.exists() and hasattr(settings, "data_dir") and settings.data_dir != data_dir:
        # Only fallback if data_dir has no raw/firms directory at all (e.g. custom slice output dir)
        if not (data_dir / "raw" / "firms").exists():
            resolved_str = pattern.replace("${TERRAFLARE_DATA_DIR}", str(settings.data_dir))
            p = Path(resolved_str)
            parent = p.parent

    if not parent.exists():
        return []
    return sorted(parent.glob(p.name))


def append_ingest_log(
    log_path: Path,
    source_id: str,
    file_name: str,
    sha256: str,
    rows_in: int,
    ingested_at: datetime,
) -> pd.DataFrame:
    """Append a record to ingest_log Parquet file idempotently."""
    record = {
        "source_id": source_id,
        "file_name": file_name,
        "sha256": sha256,
        "rows_in": int(rows_in),
        "ingested_at": ingested_at,
    }
    log_df = pd.DataFrame([record])

    if log_path.exists():
        try:
            existing_df = pd.read_parquet(log_path)
            # Remove any prior entry for the same file/sha256 to ensure idempotency
            existing_df = existing_df[
                ~((existing_df["source_id"] == source_id) & (existing_df["file_name"] == file_name))
            ]
            log_df = pd.concat([existing_df, log_df], ignore_index=True)
        except Exception:
            pass

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_df.to_parquet(log_path, index=False)
    return log_df


def ingest_file(
    file_path: Path | str,
    source_cfg: dict[str, Any],
    data_dir: Path | None = None,
    sample_n: int | None = None,
    sample_mode: str = "first",
    year: int | str | None = None,
) -> dict[str, Any]:
    """Ingest a single source CSV file.

    1. Computes SHA256.
    2. Reads raw data via adapter (supports sample_n and sample_mode).
    3. Filters by year if specified.
    4. Writes raw Parquet to data/raw/<source_id>/<stem>.parquet.
    5. Converts to canonical format (with stream determined per file).
    6. Writes canonical Parquet to data/staging/obs_all/<source_id>_<stem>.parquet.
    7. Updates ingest_log in data/staging/ingest_log.parquet and data/raw/ingest_log.parquet.

    Returns dict with summary statistics.
    """
    path = Path(file_path).resolve()
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    source_id = source_cfg.get("source_id", "unknown")
    adapter_name = source_cfg.get("adapter", "firms_csv")

    sha256 = compute_file_sha256(path)
    now_utc = datetime.now(timezone.utc)
    batch_id = f"batch_{source_id}_{path.stem}_{sha256[:8]}"

    # Instantiate adapter
    adapter_cls = registry.get(adapter_name)
    adapter = adapter_cls(source_cfg)

    # 1. Read raw file (optionally sampled with 'first' or 'spread', filtered by year chunk-by-chunk)
    raw_df = adapter.read(path, nrows=sample_n, sample_mode=sample_mode, year=year)

    # Optional year filter on raw data (supports single year or list/tuple of years)
    if year is not None and not raw_df.empty:
        years_set = {str(y) for y in year} if isinstance(year, (list, tuple, set)) else {str(year)}
        for col in ["acq_date", "date"]:
            if col in raw_df.columns:
                raw_df = raw_df[raw_df[col].astype(str).str[:4].isin(years_set)]
                break

    rows_in = len(raw_df)

    # 2. Write raw Parquet exactly as received
    raw_out_dir = base_data_dir / "raw" / source_id
    raw_out_dir.mkdir(parents=True, exist_ok=True)
    raw_out_file = raw_out_dir / f"{path.stem}.parquet"
    raw_df.to_parquet(raw_out_file, index=False)

    # 3. Convert to canonical format (stream is determined per file in to_canonical)
    canonical_df = adapter.to_canonical(raw_df, batch_id=batch_id, source_file=path.name)

    # 4. Write canonical Parquet to data/staging/obs_all/
    staging_obs_dir = base_data_dir / "staging" / "obs_all"
    staging_obs_dir.mkdir(parents=True, exist_ok=True)
    canonical_out_file = staging_obs_dir / f"{source_id}_{path.stem}.parquet"
    canonical_df.to_parquet(canonical_out_file, index=False)

    # 5. Write / append ingest log
    staging_log = base_data_dir / "staging" / "ingest_log.parquet"
    append_ingest_log(staging_log, source_id, path.name, sha256, rows_in, now_utc)

    # Also keep in data/raw for provenance tracking
    raw_log = base_data_dir / "raw" / "ingest_log.parquet"
    append_ingest_log(raw_log, source_id, path.name, sha256, rows_in, now_utc)

    return {
        "source_id": source_id,
        "file_name": path.name,
        "sha256": sha256,
        "rows_in": rows_in,
        "raw_parquet": str(raw_out_file),
        "canonical_parquet": str(canonical_out_file),
        "ingested_at": now_utc.isoformat(),
    }


def ingest_all(
    data_dir: Path | None = None,
    sources_cfg: dict[str, Any] | None = None,
    source_id_filter: str | None = None,
    sample_n: int | None = None,
    sample_mode: str = "first",
    year: int | str | None = None,
) -> dict[str, Any]:
    """Run ingestion for enabled sources in sources.yaml."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    sources = sources_cfg if sources_cfg is not None else get_sources()

    results: list[dict[str, Any]] = []
    total_rows = 0

    for source_id, cfg in sources.items():
        if source_id_filter and source_id != source_id_filter:
            continue
        if not cfg.get("enabled", True):
            continue

        loc_pattern = cfg.get("location_pattern", "")
        if not loc_pattern:
            continue

        files = resolve_location_pattern(loc_pattern, base_data_dir)
        for f in files:
            res = ingest_file(
                f,
                cfg,
                data_dir=base_data_dir,
                sample_n=sample_n,
                sample_mode=sample_mode,
                year=year,
            )
            results.append(res)
            total_rows += res["rows_in"]

    return {
        "status": "ok",
        "files_ingested": len(results),
        "total_rows": total_rows,
        "results": results,
    }
