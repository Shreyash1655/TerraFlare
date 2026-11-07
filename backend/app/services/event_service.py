
"""Feature 4 - Fire Event Intelligence: grouped hotspot activity episodes (not verified wildfires)."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, QhullError
from sklearn.cluster import DBSCAN

from app.core.config import settings
from app.utils.errors import TerraFlareError
from app.utils.response import num


LABEL = "grouped hotspot activity episodes, not verified wildfires"

LIMITATIONS = [
    "A cluster is a grouped activity episode, not a verified wildfire or a fire perimeter.",
    "The footprint is the convex hull of detections, not the burned area.",
    "Results depend on eps_km, time scale and min_samples. Try several values.",
    "No detections inside a footprint does not mean no fire (cloud, overpass gaps).",
]

_STORE: dict[str, dict] = {}


def _validate_parameters(
    eps_km,
    time_scale,
    min_samples,
    min_detections,
    limit,
):
    """Validate event detection parameters."""

    if eps_km <= 0:
        raise TerraFlareError(
            "invalid_eps_km",
            "eps_km must be greater than zero.",
            400,
        )

    if time_scale <= 0:
        raise TerraFlareError(
            "invalid_time_scale",
            "time_scale must be greater than zero.",
            400,
        )

    if min_samples < 1:
        raise TerraFlareError(
            "invalid_min_samples",
            "min_samples must be at least 1.",
            400,
        )

    if min_detections < 1:
        raise TerraFlareError(
            "invalid_min_detections",
            "min_detections must be at least 1.",
            400,
        )

    if limit < 1:
        raise TerraFlareError(
            "invalid_limit",
            "limit must be at least 1.",
            400,
        )


def _prepare_observations(obs: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean observation records before clustering."""

    required = {
        "lat",
        "lon",
        "acq_date",
    }

    missing = required - set(obs.columns)

    if missing:
        raise TerraFlareError(
            "invalid_observations",
            f"Missing required observation columns: {sorted(missing)}",
            500,
        )

    result = obs.copy()

    result["lat"] = pd.to_numeric(
        result["lat"],
        errors="coerce",
    )

    result["lon"] = pd.to_numeric(
        result["lon"],
        errors="coerce",
    )

    result["acq_date"] = pd.to_datetime(
        result["acq_date"],
        errors="coerce",
        utc=True,
    )

    if "acq_datetime_utc" in result.columns:
        result["_ts"] = pd.to_datetime(
            result["acq_datetime_utc"],
            errors="coerce",
            utc=True,
        )

        result["_ts"] = result["_ts"].fillna(
            result["acq_date"]
        )
    else:
        result["_ts"] = result["acq_date"]

    result = result.dropna(
        subset=["lat", "lon", "_ts"]
    )

    # Geographic coordinate validation.
    result = result[
        result["lat"].between(-90, 90)
        & result["lon"].between(-180, 180)
    ]

    if "sensor_family" not in result.columns:
        result["sensor_family"] = "unknown"
    else:
        result["sensor_family"] = (
            result["sensor_family"]
            .fillna("unknown")
            .astype(str)
        )

    if "frp_mw" not in result.columns:
        result["frp_mw"] = np.nan
    else:
        result["frp_mw"] = pd.to_numeric(
            result["frp_mw"],
            errors="coerce",
        )

    result = result.reset_index(drop=True)

    return result


def _footprint(
    lon: np.ndarray,
    lat: np.ndarray,
):
    """Generate an approximate convex hull from detection coordinates."""

    points = np.unique(
        np.column_stack([lon, lat]),
        axis=0,
    )

    if len(points) < 3:
        return None

    try:
        hull = ConvexHull(points)

    except QhullError:
        # Collinear or geometrically degenerate points.
        return None

    ring = points[hull.vertices].tolist()

    ring.append(ring[0])

    return {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    round(float(x), 5),
                    round(float(y), 5),
                ]
                for x, y in ring
            ]
        ],
    }


def _frp(series: pd.Series):
    """Calculate total and maximum FRP when available."""

    values = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if values.empty:
        return None, None

    return (
        num(values.sum()),
        num(values.max()),
    )


def _event_id(
    region_id,
    first,
    last,
    lat,
    lon,
    params,
):
    """Create a reproducible identifier for a detected activity episode."""

    identity = (
        f"{region_id}|"
        f"{first.isoformat()}|"
        f"{last.isoformat()}|"
        f"{lat:.4f}|"
        f"{lon:.4f}|"
        f"{params['eps_km']}|"
        f"{params['time_scale_km_per_day']}|"
        f"{params['min_samples']}"
    )

    digest = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:12]

    return f"ev_{digest}"


def detect_events(
    repo,
    region_id,
    start,
    end,
    eps_km,
    time_scale,
    min_samples,
    min_detections,
    limit,
) -> dict:

    _validate_parameters(
        eps_km,
        time_scale,
        min_samples,
        min_detections,
        limit,
    )

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    if start > end:
        raise TerraFlareError(
            "invalid_date_range",
            "Start date must not be after end date.",
            400,
        )

    params = {
        "eps_km": eps_km,
        "time_scale_km_per_day": time_scale,
        "min_samples": min_samples,
    }

    base = {
        "label": LABEL,
        "parameters": params,
        "notes": [
            "Clusters represent grouped satellite hotspot activity, not verified wildfires.",
            "The footprint is an approximate convex hull of detections, not burned area.",
        ],
    }

    observations = repo.get_observations(
        region_id,
        start,
        end,
    )

    if observations.empty:
        return {
            **base,
            "events": [],
            "n_points_processed": 0,
            "n_noise_points": 0,
            "truncated": False,
        }

    observations = _prepare_observations(
        observations
    )

    if observations.empty:
        return {
            **base,
            "events": [],
            "n_points_processed": 0,
            "n_noise_points": 0,
            "truncated": False,
            "notes": [
                "No observations with valid coordinates and timestamps were available."
            ],
        }

    if len(observations) > settings.events_max_points:
        raise TerraFlareError(
            "too_many_observations",
            (
                f"{len(observations)} detections in range "
                f"(limit {settings.events_max_points}); "
                "narrow the dates or region."
            ),
            422,
        )

    # -------------------------------------------------
    # Convert coordinates into approximate local km.
    # -------------------------------------------------

    lat = observations["lat"].to_numpy(dtype=float)
    lon = observations["lon"].to_numpy(dtype=float)

    mean_lat = float(lat.mean())
    mean_lon = float(lon.mean())

    x = (
        (lon - mean_lon)
        * 111.32
        * np.cos(np.radians(mean_lat))
    )

    y = (
        (lat - mean_lat)
        * 110.574
    )

    # -------------------------------------------------
    # Add time as a third clustering dimension.
    # -------------------------------------------------

    timestamps = observations["_ts"]

    elapsed_days = (
        timestamps - timestamps.min()
    ).dt.total_seconds().to_numpy() / 86400.0

    time_coordinate = (
        elapsed_days * time_scale
    )

    features = np.column_stack(
        [
            x,
            y,
            time_coordinate,
        ]
    )

    # -------------------------------------------------
    # DBSCAN clustering.
    # -------------------------------------------------

    labels = DBSCAN(
        eps=eps_km,
        min_samples=min_samples,
    ).fit_predict(features)

    observations = observations.assign(
        _label=labels,
    )

    events = []

    clustered = observations[
        observations["_label"] >= 0
    ]

    for cluster_label, group in clustered.groupby(
        "_label"
    ):

        if len(group) < min_detections:
            continue

        cluster_lat = float(
            group["lat"].mean()
        )

        cluster_lon = float(
            group["lon"].mean()
        )

        first = group["_ts"].min()
        last = group["_ts"].max()

        event_id = _event_id(
            region_id,
            first,
            last,
            cluster_lat,
            cluster_lon,
            params,
        )

        sensor_counts = {
            str(key): int(value)
            for key, value in group[
                "sensor_family"
            ].value_counts().items()
        }

        daily = []

        for date, daily_group in group.groupby(
            group["_ts"].dt.normalize()
        ):

            frp_sum, frp_max = _frp(
                daily_group["frp_mw"]
            )

            daily.append(
                {
                    "date": date.date().isoformat(),
                    "n_detections": int(
                        len(daily_group)
                    ),
                    "frp_sum_mw": frp_sum,
                    "frp_max_mw": frp_max,
                }
            )

        daily.sort(
            key=lambda item: item["date"]
        )

        summary = {
            "event_id": event_id,
            "first_detection": first.isoformat(),
            "last_detection": last.isoformat(),
            "n_detections": int(len(group)),
            "active_days": int(len(daily)),
            "sensors": sorted(sensor_counts),
            "n_by_sensor": sensor_counts,
            "centroid": [
                round(cluster_lon, 5),
                round(cluster_lat, 5),
            ],
            "footprint_geojson": _footprint(
                group["lon"].to_numpy(dtype=float),
                group["lat"].to_numpy(dtype=float),
            ),
            "max_frp_mw": num(
                group["frp_mw"].max()
            ),
        }

        events.append(summary)

        # Retain event details for subsequent API requests.
        if len(_STORE) > 5000:
            _STORE.clear()

        _STORE[event_id] = {
            "summary": summary,
            "daily": daily,
            "parameters": params,
        }

    events.sort(
        key=lambda event: event["n_detections"],
        reverse=True,
    )

    noise_count = int(
        (labels < 0).sum()
    )

    return {
        **base,
        "events": events[:limit],
        "n_points_processed": int(
            len(observations)
        ),
        "n_noise_points": noise_count,
        "truncated": len(events) > limit,
    }


def get_event(
    repo,
    event_id,
    region_id,
    start,
    end,
    eps_km,
    time_scale,
    min_samples,
) -> dict:

    # Recompute the same detection request if the in-memory
    # event cache is empty, for example after a server restart.

    if event_id not in _STORE:

        if (
            start is not None
            and end is not None
            and region_id is not None
            and eps_km is not None
            and time_scale is not None
            and min_samples is not None
        ):

            detect_events(
                repo=repo,
                region_id=region_id,
                start=start,
                end=end,
                eps_km=eps_km,
                time_scale=time_scale,
                min_samples=min_samples,
                min_detections=1,
                limit=10**6,
            )

    record = _STORE.get(event_id)

    if record is None:
        raise TerraFlareError(
            "event_not_found",
            (
                "Unknown event. Call /advanced/events first, "
                "or pass region_id, start, end and the same parameters."
            ),
            404,
        )

    return {
        "event_id": event_id,
        "summary": record["summary"],
        "daily": record["daily"],
        "parameters": record["parameters"],
        "label": LABEL,
    }
