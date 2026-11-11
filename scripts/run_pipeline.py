#!/usr/bin/env python3
"""TerraFlare CLI pipeline runner.

Usage examples:
    # Run full pipeline with 100-row sample per source:
    python scripts/run_pipeline.py --sample 100

    # Run clean stage only for a specific source and year:
    python scripts/run_pipeline.py --stage clean --source viirs_noaa20 --year 2023

    # Run cell_day stage:
    python scripts/run_pipeline.py --stage cell_day

    # Run with custom data directory:
    python scripts/run_pipeline.py --data-dir ../data
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' can be imported cleanly
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TerraFlare data pipeline stages (ingest, clean, cell_day, harmonize, monthly, all)."
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["all", "ingest", "clean", "cell_day", "harmonize", "monthly"],
        help="Pipeline stage to execute (default: all).",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Optional source_id filter (e.g. modis_c61, viirs_snpp, viirs_noaa20, viirs_noaa21).",
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,
        help="Optional year filter (e.g. 2023).",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Process only N rows per file for fast testing (strategy defined by --sample-mode).",
    )
    parser.add_argument(
        "--sample-mode",
        type=str,
        default="first",
        choices=["first", "spread"],
        help="Sampling mode: 'first' takes the first N rows; 'spread' takes every k-th row evenly across the file.",
    )
    parser.add_argument(
        "--method",
        type=str,
        default=None,
        choices=["stratified_ratio", "global_ratio", "count_regression", "identity"],
        help="Harmonization calibration method (default: configured in harmonization.yaml).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to data directory (default: configured settings.data_dir).",
    )
    parser.add_argument(
        "--data-version",
        type=str,
        default=None,
        help="Explicit data_version string to write to manifest (e.g. 2026.11.10.1).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Explicit run_id string for cleaning_report and execution isolation.",
    )
    parser.add_argument(
        "--keep-tables",
        action="store_true",
        help="If set, appends to existing tables rather than isolating this run's tables.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger("terraflare").setLevel(logging.DEBUG)

    try:
        results = run_pipeline(
            stage=args.stage,
            source=args.source,
            year=args.year,
            sample=args.sample,
            sample_mode=args.sample_mode,
            method_id=args.method,
            data_dir=args.data_dir,
            data_version=args.data_version,
            run_id=args.run_id,
            clear_tables=not args.keep_tables,
        )
        print("\n=== PIPELINE RUN SUMMARY ===")
        manifest = results.get("manifest", {})
        print(f"Data Version : {manifest.get('data_version')}")
        print(f"Git Commit   : {manifest.get('git_commit')}")
        print(f"Date Range   : {manifest.get('date_range')}")
        print(f"Row Counts   : {json.dumps(manifest.get('row_counts'), indent=2)}")
        print(f"DuckDB Synced: {results.get('duckdb_synced')}")
        return 0
    except Exception as exc:
        print(f"Error executing pipeline: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

