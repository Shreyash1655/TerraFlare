from __future__ import annotations

from app.utils.errors import TerraFlareError


def parse_bbox(bbox: str | None):
    """'min_lon,min_lat,max_lon,max_lat' -> [x0, y0, x1, y1] or None."""
    if not bbox:
        return None
    try:
        a = [float(x) for x in bbox.split(",")]
    except ValueError:
        raise TerraFlareError("invalid_bbox", "bbox must be four numbers: min_lon,min_lat,max_lon,max_lat", 400)
    if len(a) != 4:
        raise TerraFlareError("invalid_bbox", "bbox must be four numbers: min_lon,min_lat,max_lon,max_lat", 400)
    x0, y0, x1, y1 = a
    if not (-180 <= x0 < x1 <= 180 and -90 <= y0 < y1 <= 90):
        raise TerraFlareError("invalid_bbox", "bbox out of range or min >= max", 400)
    return a


class FilteredRepo:
    """Delegates everything to the real repo; get_observations is cut by bbox and sensor family."""

    def __init__(self, repo, bbox: str | None = None, sensor: str | None = None):
        self._repo = repo
        self._bbox = parse_bbox(bbox)
        self._sensor = sensor

    def __getattr__(self, name):
        return getattr(self._repo, name)

    def get_observations(self, region_id=None, start=None, end=None, sensors=None, valid_only=True):
        df = self._repo.get_observations(region_id, start, end, sensors, valid_only)
        if self._sensor:
            df = df[df["sensor_family"].astype(str).str.upper() == self._sensor.upper()]
        if self._bbox:
            x0, y0, x1, y1 = self._bbox
            df = df[(df["lon"] >= x0) & (df["lon"] <= x1) & (df["lat"] >= y0) & (df["lat"] <= y1)]
        return df