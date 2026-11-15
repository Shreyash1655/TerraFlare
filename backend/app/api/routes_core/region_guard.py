from fastapi import HTTPException

NO_FILTER_ALIASES = {"global", "india"}
MIN_VIIRS_COVERAGE = 1000  # detections/day below this = partial coverage


def resolve_region(region_id: str | None, supported: list[str] | None = None) -> str:
    supported = supported or []
    rid = (region_id or "global").strip().lower()
    if rid in NO_FILTER_ALIASES or rid in {s.lower() for s in supported}:
        return rid
    allowed = sorted(NO_FILTER_ALIASES | set(supported))
    raise HTTPException(
        status_code=404,
        detail=f"Region '{region_id}' not found. Supported regions: {', '.join(allowed)}",
    )


def clean_series(series: list[dict]) -> list[dict]:
    for p in series:
        v = p.get("viirs_observed")
        if v is None or v < MIN_VIIRS_COVERAGE:
            p["harmonized_value"] = p["lower"] = p["upper"] = None
        elif p.get("lower") == p.get("upper") == p.get("harmonized_value"):
            p["lower"] = p["upper"] = None  # no fake zero-width interval
    return series