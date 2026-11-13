#!/usr/bin/env python3
"""TerraFlare Serving Data Packaging Utility.

Copies only the minimal artifact files required by the Core API into a serving
directory (data_serving/) and outputs a detailed size audit table.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def package_serving_data(
    src_dir: Path,
    dest_dir: Path,
    include_cell_day: bool = True,
) -> dict[str, int]:
    """Copy only serving files into dest_dir and return dict of relative paths to sizes."""
    src_dir = src_dir.resolve()
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied_files: dict[str, int] = {}

    # 1. Manifest
    manifest_src = src_dir / "manifest.json"
    if manifest_src.exists():
        manifest_dest = dest_dir / "manifest.json"
        shutil.copy2(manifest_src, manifest_dest)
        copied_files["manifest.json"] = manifest_dest.stat().st_size

    # 2. DuckDB Database
    duckdb_src = src_dir / "terraflare.duckdb"
    if duckdb_src.exists():
        duckdb_dest = dest_dir / "terraflare.duckdb"
        shutil.copy2(duckdb_src, duckdb_dest)
        copied_files["terraflare.duckdb"] = duckdb_dest.stat().st_size

    # 3. Serving Marts
    marts_src = src_dir / "marts"
    marts_dest = dest_dir / "marts"
    marts_dest.mkdir(parents=True, exist_ok=True)

    serving_mart_names = [
        "harmonized_cell_day.parquet",
        "monthly_activity.parquet",
        "calibration_models.parquet",
        "cleaning_report.parquet",
        "ingest_log.parquet",
        "cell_month_activity.parquet",
        "precomputed_baselines.parquet",
        "baselines.parquet",
    ]
    if include_cell_day:
        serving_mart_names.insert(0, "cell_day_activity.parquet")

    if marts_src.exists():
        for name in serving_mart_names:
            f_src = marts_src / name
            if f_src.exists():
                f_dest = marts_dest / name
                shutil.copy2(f_src, f_dest)
                rel_path = f"marts/{name}"
                copied_files[rel_path] = f_dest.stat().st_size

    # Also copy staging reports if they exist and weren't in marts
    staging_src = src_dir / "staging"
    if staging_src.exists():
        staging_dest = dest_dir / "staging"
        staging_dest.mkdir(parents=True, exist_ok=True)
        for name in ["static_source_mask.json", "cleaning_report.parquet", "ingest_log.parquet"]:
            f_src = staging_src / name
            if f_src.exists():
                f_dest = staging_dest / name
                shutil.copy2(f_src, f_dest)
                rel_path = f"staging/{name}"
                copied_files[rel_path] = f_dest.stat().st_size

    # Re-sync views in packaged duckdb relative to dest_dir
    duckdb_dest = dest_dir / "terraflare.duckdb"
    if duckdb_dest.exists():
        try:
            sys.path.insert(0, str(REPO_ROOT / "backend"))
            from app.core.storage.schema_sql import create_views
            import duckdb
            con = duckdb.connect(str(duckdb_dest), read_only=False)
            create_views(con, dest_dir, as_temp=False)
            con.close()
        except Exception as e:
            print(f"Notice: view resync in packaged duckdb skipped ({e})")

    return copied_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package serving data for TerraFlare Core API."
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=REPO_ROOT / "data",
        help="Source data directory (default: data/)",
    )
    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=REPO_ROOT / "data_serving",
        help="Destination directory for API serving files (default: data_serving/)",
    )
    parser.add_argument(
        "--no-cell-day",
        action="store_true",
        help="Exclude cell_day_activity.parquet from serving package (reduces bundle size).",
    )
    args = parser.parse_args()

    src_dir = args.src_dir.resolve()
    dest_dir = args.dest_dir.resolve()

    print("=" * 80)
    print(" TerraFlare Serving Data Packager")
    print("=" * 80)
    print(f"Source Directory:      {src_dir}")
    print(f"Destination Directory: {dest_dir}")
    print("-" * 80)

    if not src_dir.exists():
        print(f"ERROR: Source directory {src_dir} does not exist.")
        return 1

    copied = package_serving_data(
        src_dir=src_dir,
        dest_dir=dest_dir,
        include_cell_day=not args.no_cell_day,
    )

    if not copied:
        print("WARNING: No serving files were found to package.")
        return 1

    total_bytes = 0
    print(f"{'Serving File':<45} | {'Size':>15} | {'Bytes':>15}")
    print("-" * 80)
    for rel_path, file_size in sorted(copied.items()):
        total_bytes += file_size
        print(f"{rel_path:<45} | {format_bytes(file_size):>15} | {file_size:>15,d}")

    print("-" * 80)
    print(f"{'Total Serving Package Bundle':<45} | {format_bytes(total_bytes):>15} | {total_bytes:>15,d}")
    print("=" * 80)
    print(f"Packaging complete! Ready to ship {dest_dir.name}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

