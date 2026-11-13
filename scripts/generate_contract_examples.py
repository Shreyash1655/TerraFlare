"""Generate contracts/examples/*.json from small REAL responses for Member 2.

All responses are queried directly from the real data lake (DuckDB marts)
and adhere to the standard {data, meta} envelope.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Ensure real data mode is active
os.environ["TERRAFLARE_DATA_MODE"] = "real"
import sys
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
from app.api.routes_core.hotspots import get_hotspot_cells, get_hotspots
from app.api.routes_core.meta import get_capabilities
from app.api.routes_core.regions import get_regions


def to_jsonable(obj: Any) -> Any:
    """Recursively convert Pydantic models and dictionaries into JSON-serializable primitives."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    return obj


def main() -> None:
    output_dir = Path("contracts/examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating contract examples into {output_dir.resolve()}...")

    # 1. Health
    print("  -> Generating health.json...")
    res_health = to_jsonable(health())
    (output_dir / "health.json").write_text(json.dumps(res_health, indent=2), encoding="utf-8")

    # 2. Meta Capabilities
    print("  -> Generating meta_capabilities.json...")
    res_meta = to_jsonable(get_capabilities())
    (output_dir / "meta_capabilities.json").write_text(json.dumps(res_meta, indent=2), encoding="utf-8")

    # 3. Regions
    print("  -> Generating regions.json...")
    res_regions = to_jsonable(get_regions())
    (output_dir / "regions.json").write_text(json.dumps(res_regions, indent=2), encoding="utf-8")

    # 4. Hotspots (small real sample: limit=5)
    print("  -> Generating hotspots.json...")
    res_hotspots = to_jsonable(get_hotspots(region_id="north_india", limit=5, start="2026-11-01"))
    (output_dir / "hotspots.json").write_text(json.dumps(res_hotspots, indent=2), encoding="utf-8")

    # 5. Hotspot Cells (small real bbox in Punjab)
    print("  -> Generating hotspots_cells.json...")
    res_cells = to_jsonable(get_hotspot_cells(bbox="76.0,30.0,76.5,30.5", start="2026-11-01"))
    # Limit cells array to 10 items for a clean, concise contract example
    if "data" in res_cells and "cells" in res_cells["data"]:
        res_cells["data"]["cells"] = res_cells["data"]["cells"][:10]
    (output_dir / "hotspots_cells.json").write_text(json.dumps(res_cells, indent=2), encoding="utf-8")

    # 6. Calendar (recent 14 days sample from real 2026 calendar)
    print("  -> Generating calendar.json...")
    res_calendar = to_jsonable(get_calendar(region_id="north_india", year=2026))
    if "data" in res_calendar and "days" in res_calendar["data"]:
        # Keep last 14 days for a compact contract example
        res_calendar["data"]["days"] = res_calendar["data"]["days"][-14:]
    (output_dir / "calendar.json").write_text(json.dumps(res_calendar, indent=2), encoding="utf-8")

    # 7. Yearly History
    print("  -> Generating history_yearly.json...")
    res_yearly = to_jsonable(get_yearly_history(region_id="india"))
    (output_dir / "history_yearly.json").write_text(json.dumps(res_yearly, indent=2), encoding="utf-8")

    # 8. Monthly History (slice of recent 24 months for compact contract example)
    print("  -> Generating history_monthly.json...")
    res_monthly = to_jsonable(get_monthly_history(region_id="north_india", series="harmonized"))
    if "data" in res_monthly and "matrix" in res_monthly["data"]:
        res_monthly["data"]["matrix"] = res_monthly["data"]["matrix"][-24:]
    (output_dir / "history_monthly.json").write_text(json.dumps(res_monthly, indent=2), encoding="utf-8")

    # 9. Current vs Median
    print("  -> Generating history_current_vs_median.json...")
    res_cvm = to_jsonable(get_current_vs_median(region_id="india"))
    (output_dir / "history_current_vs_median.json").write_text(json.dumps(res_cvm, indent=2), encoding="utf-8")

    # 10. Harmonization Comparison (recent 12 months)
    print("  -> Generating harmonization_comparison.json...")
    res_cmp = to_jsonable(get_comparison(region_id="india", granularity="month"))
    if "data" in res_cmp and "series" in res_cmp["data"]:
        res_cmp["data"]["series"] = res_cmp["data"]["series"][-12:]
    (output_dir / "harmonization_comparison.json").write_text(json.dumps(res_cmp, indent=2), encoding="utf-8")

    # 11. Harmonization Method
    print("  -> Generating harmonization_method.json...")
    res_method = to_jsonable(get_harmonization_method())
    (output_dir / "harmonization_method.json").write_text(json.dumps(res_method, indent=2), encoding="utf-8")

    # 12. Export CSV sample
    print("  -> Generating export_sample.csv...")
    res_export = export_csv(dataset="monthly", region_id="north_india", start="2026-10-01")
    csv_text = res_export.raw_content.decode("utf-8")
    (output_dir / "export_sample.csv").write_text(csv_text, encoding="utf-8")

    print(f"Successfully generated all contract examples in {output_dir.resolve()}.")


if __name__ == "__main__":
    main()
