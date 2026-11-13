"""Core API route: /api/v1/regions with common envelope."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.shared.api_envelope import ApiResponse, ResponseMeta, make_meta
from app.shared.regions import load_regions

router = APIRouter(tags=["regions"])


class RegionItem(BaseModel):
    region_id: str
    name: str
    bbox: list[float]
    description: str | None = None


class RegionsData(BaseModel):
    regions: list[RegionItem]


class RegionsEnvelope(ApiResponse[RegionsData]):
    pass


@router.get("/regions", response_model=RegionsEnvelope)
def get_regions() -> dict[str, Any]:
    """List supported regions with their bounding boxes wrapped in common envelope."""
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
    data = RegionsData(regions=items)
    meta = make_meta()
    return {"data": data, "meta": meta}
