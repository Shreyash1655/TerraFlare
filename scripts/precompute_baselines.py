"""Pre-compute monthly baselines for configured regions.

Usage:
    python scripts/precompute_baselines.py [--data-dir PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.analytics.area_monthly import precompute_configured_baselines
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("precompute_baselines")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-compute historical baselines for configured regions.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Base data directory")
    parser.add_argument("--output", type=Path, default=None, help="Output parquet path")
    args = parser.parse_args()

    data_dir = args.data_dir or settings.data_dir
    output_path = args.output or (data_dir / "marts" / "baselines.parquet")

    logger.info(f"Precomputing baselines using data from {data_dir}...")
    df = precompute_configured_baselines(data_dir=data_dir, output_path=output_path)
    logger.info(f"Done! Computed {len(df)} baseline rows. Saved to {output_path}")


if __name__ == "__main__":
    main()
