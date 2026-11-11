#!/usr/bin/env python3
"""Compare Canonical Schema vs obs_clean Schema and recompute bytes per row for old vs new storage settings."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

# Add backend directory to sys.path so 'app' can be imported cleanly
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd

from app.settings import settings
from app.shared.canonical import CANONICAL_COLUMNS, CANONICAL_DTYPES


def print_schema_comparison(obs_clean_cols: list[str]) -> list[str]:
    """Print the side-by-side comparison of Canonical Schema vs obs_clean Schema."""
    print("=" * 80)
    print(f"{'COLUMN NAME':<25} | {'CANONICAL DTYPE':<18} | {'OBS_CLEAN STATUS':<18}")
    print("=" * 80)

    dropped = []
    for col in CANONICAL_COLUMNS:
        dt = str(CANONICAL_DTYPES.get(col, "object"))
        if col in obs_clean_cols:
            status = "Kept"
        else:
            status = "DROPPED"
            dropped.append(col)
        print(f"{col:<25} | {dt:<18} | {status:<18}")

    print("=" * 80)
    print(f"Total Canonical Columns : {len(CANONICAL_COLUMNS)}")
    print(f"Total obs_clean Columns : {len(obs_clean_cols)}")
    print(f"Dropped Columns         : {dropped}")
    print("=" * 80)
    return dropped


def recompute_storage_metrics(sample_df: pd.DataFrame) -> dict[str, float]:
    """Recompute bytes per row on the exact same sample under old and new storage settings."""
    n_rows = len(sample_df)
    if n_rows == 0:
        return {"old_bytes_per_row": 0.0, "new_bytes_per_row": 0.0, "reduction_pct": 0.0}

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Old baseline: unhashed obs_id, extras kept, snappy compression
        old_df = sample_df.copy()
        old_file = tmp_path / "obs_clean_old.parquet"
        old_df.to_parquet(old_file, index=False, compression="snappy")
        old_size_bytes = old_file.stat().st_size
        old_bpr = old_size_bytes / n_rows

        # 2. New setting: 16-char hash obs_id, extras dropped, zstd compression
        new_df = sample_df.copy()
        if "obs_id" in new_df.columns:
            new_df["obs_id"] = new_df["obs_id"].apply(
                lambda x: hashlib.sha256(str(x).encode("utf-8")).hexdigest()[:16] if pd.notna(x) else ""
            )
        if "extras" in new_df.columns:
            new_df = new_df.drop(columns=["extras"])

        new_file = tmp_path / "obs_clean_new.parquet"
        new_df.to_parquet(new_file, index=False, compression="zstd")
        new_size_bytes = new_file.stat().st_size
        new_bpr = new_size_bytes / n_rows

        reduction_pct = ((old_bpr - new_bpr) / old_bpr) * 100.0

        print(f"\nStorage Recomputation on Exact Sample ({n_rows:,} rows):")
        print(f"- Old Baseline (snappy, full unhashed obs_id, with extras):")
        print(f"  File Size      : {old_size_bytes:,} bytes ({old_size_bytes / (1024*1024):.2f} MB)")
        print(f"  Bytes per Row  : {old_bpr:.2f} B/row")
        print(f"- New Settings (zstd, 16-char sha256 obs_id, extras dropped):")
        print(f"  File Size      : {new_size_bytes:,} bytes ({new_size_bytes / (1024*1024):.2f} MB)")
        print(f"  Bytes per Row  : {new_bpr:.2f} B/row")
        print(f"- Storage Reduction: {reduction_pct:.1f}% reduction")
        print("=" * 80)

        return {
            "n_rows": n_rows,
            "old_file_size": old_size_bytes,
            "new_file_size": new_size_bytes,
            "old_bytes_per_row": round(old_bpr, 2),
            "new_bytes_per_row": round(new_bpr, 2),
            "reduction_pct": round(reduction_pct, 1),
        }


def main() -> int:
    # 1. Inspect obs_clean columns
    obs_clean_path = settings.data_dir / "staging" / "obs_clean.parquet"
    if not obs_clean_path.exists():
        # Fall back to slice dir
        obs_clean_path = REPO_ROOT / "data" / "slice_2019_2022" / "staging" / "obs_clean.parquet"

    clean_cols = [c for c in CANONICAL_COLUMNS if c != "extras"]
    if obs_clean_path.exists():
        try:
            df_hdr = pd.read_parquet(obs_clean_path, columns=None)
            clean_cols = list(df_hdr.columns)
        except Exception:
            pass

    dropped = print_schema_comparison(clean_cols)

    # 2. Recompute storage metrics on sample of canonical observations (with extras)
    obs_all_dir = settings.data_dir / "staging" / "obs_all"
    if not obs_all_dir.exists() or not list(obs_all_dir.glob("*.parquet")):
        obs_all_dir = REPO_ROOT / "data" / "slice_2019_2022" / "staging" / "obs_all"

    files = list(obs_all_dir.glob("*.parquet")) if obs_all_dir.exists() else []
    sample_df = pd.DataFrame()

    if files:
        chunks = []
        rows_needed = 100000
        for f in files:
            cdf = pd.read_parquet(f)
            chunks.append(cdf)
            if sum(len(c) for c in chunks) >= rows_needed:
                break
        if chunks:
            sample_df = pd.concat(chunks, ignore_index=True).head(rows_needed)

    if sample_df.empty:
        # Build synthetic canonical sample for comparison
        from app.shared.canonical import empty_canonical_df
        sample_df = empty_canonical_df()
        synthetic_rows = []
        for i in range(10000):
            synthetic_rows.append({
                "obs_id": f"obs_{hashlib.sha256(str(i).encode()).hexdigest()}",
                "source_id": "viirs_noaa20",
                "sensor_family": "VIIRS",
                "platform": "NOAA-20",
                "processing_stream": "SP",
                "product_version": "2.0",
                "ingest_batch_id": "batch_test_12345678",
                "acq_date": "2023-05-01",
                "lat": 28.6139,
                "lon": 77.2090,
                "h3_cell": "866189247ffffff",
                "confidence_raw": "nominal",
                "confidence_class": "nominal",
                "frp_mw": 15.4,
                "day_night": "D",
                "fire_type": "0",
                "is_valid": True,
                "qc_flags": "[]",
                "is_synthetic": False,
                "extras": '{"scan": 0.4, "track": 0.4, "bright_ti4": 330.5, "bright_ti5": 295.2, "version": "2.0"}',
            })
        sample_df = pd.DataFrame(synthetic_rows)

    metrics = recompute_storage_metrics(sample_df)
    return 0


if __name__ == "__main__":
    sys.exit(main())

