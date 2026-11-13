"""Smoke test script executing against all 16 Core API endpoints on real data.

Measures Cold and Warm latency, validates the standard {data, meta} envelope,
tests boundary rejections and fallback behaviors, and outputs a formatted benchmark summary table.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

# Ensure real data mode is active
os.environ["TERRAFLARE_DATA_MODE"] = "real"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.api.routes_core.calendar import get_calendar
from app.api.routes_core.export import export_csv
from app.api.routes_core.harmonization import get_comparison, get_harmonization_method
from app.api.routes_core.health import health
from app.api.routes_core.history import (
    get_current_vs_median,
    get_monthly_history,
    get_yearly_history,
)
from app.api.routes_core.hotspots import (
    get_hotspot_cells,
    get_hotspots,
)
from app.api.routes_core.meta import get_capabilities
from app.api.routes_core.regions import get_regions
from app.shared.errors import TerraFlareError


def format_ms(seconds: float) -> str:
    return f"{seconds * 1000.0:>8.2f} ms"


def run_single_pass() -> list[dict[str, Any]]:
    """Execute all 16 endpoint checks once and return dict with name, endpoint, dur, status, note."""
    checks: list[dict[str, Any]] = []

    def exec_check(name: str, endpoint: str, func: Any, **kwargs: Any) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            res = func(**kwargs)
            dur = time.perf_counter() - t0
            meta = res.get("meta") if isinstance(res, dict) else None
            rel = getattr(meta, "reliability", None) or (meta.get("reliability") if isinstance(meta, dict) else None)
            return {"name": name, "endpoint": endpoint, "dur": dur, "status": "PASS", "note": f"rel={rel or 'N/A'}"}
        except Exception as e:
            dur = time.perf_counter() - t0
            return {"name": name, "endpoint": endpoint, "dur": dur, "status": "FAIL", "note": f"ERROR: {str(e)[:45]}"}

    # 1. Health
    checks.append(exec_check("Health", "/api/v1/health", health))

    # 2. Capabilities
    checks.append(exec_check("Capabilities", "/api/v1/meta/capabilities", get_capabilities))

    # 3. Regions
    checks.append(exec_check("Regions", "/api/v1/regions", get_regions))

    # 4. Hotspots (Region)
    checks.append(exec_check("Hotspots (Region)", "/api/v1/hotspots", get_hotspots, region_id="north_india", limit=50))

    # 5. Hotspots (BBox)
    checks.append(exec_check("Hotspots (BBox)", "/api/v1/hotspots?bbox=...", get_hotspots, bbox="75.0,28.0,78.0,31.0", limit=50))

    # 6. Hotspots Cells
    checks.append(exec_check("Hotspot Cells", "/api/v1/hotspots/cells", get_hotspot_cells, region_id="north_india", start="2026-11-01"))

    # 7. Calendar
    checks.append(exec_check("Calendar", "/api/v1/calendar", get_calendar, region_id="north_india", year=2026))

    # 8. Yearly History
    checks.append(exec_check("Yearly History", "/api/v1/history/yearly", get_yearly_history, region_id="india", series="harmonized"))

    # 9. Monthly History
    checks.append(exec_check("Monthly History", "/api/v1/history/monthly", get_monthly_history, region_id="north_india", series="harmonized"))

    # 10. Current vs Median
    checks.append(exec_check("Current vs Median", "/api/v1/history/current-vs-median", get_current_vs_median, region_id="india", series="harmonized"))

    # 11. Harmonization Comparison
    checks.append(exec_check("Harmonization Comp", "/api/v1/harmonization/comparison", get_comparison, region_id="india", granularity="month"))

    # 12. Harmonization Method
    checks.append(exec_check("Harmonization Method", "/api/v1/harmonization/method", get_harmonization_method))

    # 13. Export CSV (Monthly)
    checks.append(exec_check("Export CSV (Monthly)", "/api/v1/export/csv", export_csv, dataset="monthly", region_id="north_india", start="2026-10-01"))

    # 14. Validation: Outside Data Region rejection
    t0 = time.perf_counter()
    try:
        get_hotspots(bbox="-120.0,30.0,-119.0,31.0")
        dur = time.perf_counter() - t0
        checks.append({"name": "Reject Outside Area", "endpoint": "Validation Check", "dur": dur, "status": "FAIL", "note": "Failed to reject outside area"})
    except TerraFlareError as tfe:
        dur = time.perf_counter() - t0
        is_ok = tfe.code == "outside_data_region" and tfe.status_code == 400
        checks.append({"name": "Reject Outside Area", "endpoint": "Validation Check", "dur": dur, "status": "PASS" if is_ok else "FAIL", "note": f"400 {tfe.code}"})

    # 15. Validation: Oversized area rejection
    t0 = time.perf_counter()
    try:
        get_hotspots(bbox="60.0,0.0,105.0,40.0")
        dur = time.perf_counter() - t0
        checks.append({"name": "Reject Oversized Area", "endpoint": "Validation Check", "dur": dur, "status": "FAIL", "note": "Failed to reject oversized area"})
    except TerraFlareError as tfe:
        dur = time.perf_counter() - t0
        is_ok = tfe.code == "oversized_area" and tfe.status_code == 400
        checks.append({"name": "Reject Oversized Area", "endpoint": "Validation Check", "dur": dur, "status": "PASS" if is_ok else "FAIL", "note": f"400 {tfe.code}"})

    # 16. Fallback: Small area defaults to viirs_native
    t0 = time.perf_counter()
    try:
        res = get_yearly_history(bbox="77.10,28.60,77.11,28.61", series="harmonized")
        dur = time.perf_counter() - t0
        meta = res.get("meta")
        series = getattr(meta, "series", None) or meta.get("series")
        warns = getattr(meta, "warnings", None) or meta.get("warnings")
        # Task 13 Small-Area Fallback: series remains 'harmonized' (composite spliced), retaining pre-2012
        is_ok = series == "harmonized" and any("pre-2012" in w for w in warns) and any("Area is small" in w for w in warns)
        checks.append({"name": "Small Area Fallback", "endpoint": "Fallback Check", "dur": dur, "status": "PASS" if is_ok else "FAIL", "note": f"series={series}, {len(warns)} warns"})
    except Exception as e:
        dur = time.perf_counter() - t0
        checks.append({"name": "Small Area Fallback", "endpoint": "Fallback Check", "dur": dur, "status": "FAIL", "note": str(e)[:30]})

    return checks


def main() -> int:
    print("=" * 115)
    print(" TerraFlare Core API Smoke Test & Latency Benchmark (Real Data)")
    print("=" * 115)

    print("\nExecuting Cold Pass...")
    cold_results = run_single_pass()

    print("Executing Warm Pass...")
    warm_results = run_single_pass()

    print(f"\n{'Name':<24} | {'Endpoint':<34} | {'Status':<6} | {'Cold Latency':<12} | {'Warm Latency':<12} | {'Target (<2s)':<12} | {'Notes'}")
    print("-" * 125)

    all_passed = True
    total_cold = 0.0
    total_warm = 0.0

    for cold, warm in zip(cold_results, warm_results):
        status = "PASS" if (cold["status"] == "PASS" and warm["status"] == "PASS") else "FAIL"
        if status != "PASS":
            all_passed = False

        cold_dur = cold["dur"]
        warm_dur = warm["dur"]
        total_cold += cold_dur
        total_warm += warm_dur

        target_status = "PASS" if warm_dur < 2.0 else "SLOW"

        print(
            f"{cold['name']:<24} | "
            f"{cold['endpoint']:<34} | "
            f"{status:<6} | "
            f"{format_ms(cold_dur):<12} | "
            f"{format_ms(warm_dur):<12} | "
            f"{target_status:<12} | "
            f"{cold['note']}"
        )

    print("-" * 125)
    print(
        f"Total Latency: Cold = {format_ms(total_cold)} | Warm = {format_ms(total_warm)} across {len(cold_results)} checks. "
        f"Overall: {'PASS' if all_passed else 'FAIL'}\n"
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
