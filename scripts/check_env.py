#!/usr/bin/env python3
"""Check TerraFlare environment status safely without exposing secrets."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' can be imported cleanly
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.settings import settings


def main() -> int:
    has_key = bool(settings.firms_map_key and str(settings.firms_map_key).strip())
    print("TerraFlare Environment Status:")
    print(f"  FIRMS_MAP_KEY is set: {has_key}")
    print(f"  Data directory:       {settings.data_dir}")
    print(f"  Data mode:           {settings.data_mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

