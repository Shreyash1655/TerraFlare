"""Core API route: /api/v1/regions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.shared.regions import load_regions

router = APIRouter(tags=["regions"])


class RegionItem(BaseModel):
    region_id: str
    name: str
    bbox: list[float]
    description: str | None = None


class RegionsResponse(BaseModel):
    regions: list[RegionItem]


@router.get("/regions", response_model=RegionsResponse)
def get_regions() -> dict[str, Any]:
    """List supported regions with their bounding boxes."""
    regions_map = load_regions()
    items = []
    for r in regions_map.values():
        items.append(
            RegionItem(
                region_id=r.region_id,
                name=r.name,
                bbox=[r.bbox.min_lon, r.bbox.min_lat, r.bbox.max_lon, r.bbox.max_lat],
                description=r.description.strip() if r.description else None,
            )
        )
    return {"regions": items}
