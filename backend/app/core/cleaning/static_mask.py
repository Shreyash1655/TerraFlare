"""Static source detection mask for NRT fire observations using fine H3 grid."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h3
import pandas as pd

from app.core.cleaning.rules import _append_qc_flag
from app.shared.config_loader import get_harmonization_config


def get_static_mask_config() -> dict[str, Any]:
    """Read static_source_mask config from harmonization.yaml."""
    harm_cfg = get_harmonization_config()
    mask_cfg = harm_cfg.get("static_source_mask", {})
    return {
        "h3_resolution": int(mask_cfg.get("h3_resolution", 8)),
        "min_distinct_days": int(mask_cfg.get("min_distinct_days", 3)),
        "min_static_pct": float(mask_cfg.get("min_static_pct", 50.0)),
        "static_types": [str(t) for t in mask_cfg.get("static_types", [2, 3])],
    }


def build_static_source_mask(
    archive_df: pd.DataFrame,
    h3_resolution: int = 8,
    min_distinct_days: int = 3,
    min_static_pct: float = 50.0,
    static_types: list[str] | set[str] | None = None,
) -> set[tuple[str, str]]:
    """Build a set of (platform, h3_cell_res8) tuples considered static sources.

    Selected cells satisfy two conditions:
    1. Archive detections of type 2 or 3 occur on at least min_distinct_days distinct days.
    2. At least min_static_pct (default 50%) of all archive detections in that cell for that platform
       are type 2 or 3.
    """
    if archive_df.empty or "fire_type" not in archive_df.columns:
        return set()

    types = set(static_types) if static_types else {"2", "3"}
    valid_coords = archive_df["lat"].notna() & archive_df["lon"].notna()
    if not valid_coords.any():
        return set()

    sub = archive_df.loc[valid_coords, ["platform", "lat", "lon", "acq_date", "fire_type"]].copy()

    # Fast unique lat/lon to H3 resolution 8 mapping
    coords = sub[["lat", "lon"]].drop_duplicates()
    coord_to_cell: dict[tuple[float, float], str] = {}
    for r in coords.itertuples(index=False):
        try:
            coord_to_cell[(r.lat, r.lon)] = h3.latlng_to_cell(float(r.lat), float(r.lon), h3_resolution)
        except Exception:
            continue

    sub["h3_cell_res8"] = [
        coord_to_cell.get((la, lo)) for la, lo in zip(sub["lat"], sub["lon"])
    ]
    sub = sub[sub["h3_cell_res8"].notna()]
    if sub.empty:
        return set()

    type_str = sub["fire_type"].astype(str).str.strip().str.replace(".0", "", regex=False)
    sub["_is_static"] = type_str.isin(types)

    # Vectorized counts per (platform, h3_cell_res8)
    total_counts = sub.groupby(["platform", "h3_cell_res8"]).size()
    static_sub = sub[sub["_is_static"]]
    if static_sub.empty:
        return set()

    static_counts = static_sub.groupby(["platform", "h3_cell_res8"]).size()
    distinct_static_days = static_sub.groupby(["platform", "h3_cell_res8"])["acq_date"].nunique()

    stats = pd.DataFrame({
        "total_detections": total_counts,
        "static_detections": static_counts,
        "distinct_static_days": distinct_static_days,
    }).fillna(0)

    stats["static_pct"] = (stats["static_detections"] / stats["total_detections"]) * 100.0

    qualifying = stats[
        (stats["distinct_static_days"] >= min_distinct_days)
        & (stats["static_pct"] >= min_static_pct)
    ].index

    return set(qualifying)


def apply_static_source_mask(
    df: pd.DataFrame,
    mask: set[tuple[str, str]],
    h3_resolution: int = 8,
) -> tuple[pd.DataFrame, int, int]:
    """Flag NRT rows falling in the static-source mask as 'possible_static_source'.

    Note: Rows are flagged, NOT dropped (is_valid remains unchanged).
    Also performs a consistency check counting how many archive rows fall into the mask.

    Returns:
        (df_with_flags, nrt_flagged_count, archive_in_mask_count)
    """
    if df.empty or not mask or "lat" not in df.columns or "lon" not in df.columns:
        return df, 0, 0

    out = df.copy()
    valid_coords = out["lat"].notna() & out["lon"].notna()
    if not valid_coords.any():
        return out, 0, 0

    # Compute H3 cells at resolution 8 on unique pairs
    coords = out.loc[valid_coords, ["lat", "lon"]].drop_duplicates()
    coord_to_cell: dict[tuple[float, float], str] = {}
    for r in coords.itertuples(index=False):
        try:
            coord_to_cell[(r.lat, r.lon)] = h3.latlng_to_cell(float(r.lat), float(r.lon), h3_resolution)
        except Exception:
            continue

    cells_res8 = [
        coord_to_cell.get((la, lo)) if pd.notna(la) and pd.notna(lo) else None
        for la, lo in zip(out["lat"], out["lon"])
    ]

    # Check membership in mask
    in_mask_series = pd.Series(
        [(plat, c) in mask if c else False for plat, c in zip(out["platform"], cells_res8)],
        index=out.index,
    )

    if "processing_stream" in out.columns:
        is_nrt = out["processing_stream"].astype(str).isin(["NRT", "nrt"])
    else:
        is_nrt = pd.Series(False, index=out.index)
    is_sp = ~is_nrt

    if "static_masked" not in out.columns:
        out["static_masked"] = False

    # Check archive static rows (type 2 or 3)
    if "fire_type" in out.columns:
        ft_cleaned = out["fire_type"].astype(str).str.strip().str.replace(".0", "", regex=False)
        archive_static = ft_cleaned.isin(["2", "3"])
    else:
        archive_static = pd.Series(False, index=out.index)

    # Flag NRT rows in static mask and assign static_masked boolean
    nrt_mask = is_nrt & in_mask_series
    out["static_masked"] = (nrt_mask | archive_static).astype(bool)

    nrt_flagged = int(nrt_mask.sum())
    if nrt_flagged > 0:
        out.loc[nrt_mask, "qc_flags"] = out.loc[nrt_mask, "qc_flags"].apply(
            lambda existing: _append_qc_flag(existing, "possible_static_source")
        )

    # Consistency check on archive rows
    archive_in_mask = int((is_sp & in_mask_series).sum())

    return out, nrt_flagged, archive_in_mask


def compute_static_mask_metrics(
    df: pd.DataFrame,
    mask: set[tuple[str, str]],
    h3_resolution: int = 8,
) -> dict[str, Any]:
    """Compute share metrics for static source mask:
    - Share of NRT rows flagged
    - Share of archive type-0 (vegetation) rows falling inside mask
    - Share of archive type 2/3 (static land / offshore) rows falling inside mask
    """
    if df.empty or not mask or "lat" not in df.columns or "lon" not in df.columns:
        return {
            "total_nrt": 0,
            "nrt_flagged": 0,
            "nrt_flagged_share": 0.0,
            "total_archive_type0": 0,
            "archive_type0_in_mask": 0,
            "archive_type0_share": 0.0,
            "total_archive_static": 0,
            "archive_static_in_mask": 0,
            "archive_static_share": 0.0,
        }

    valid_coords = df["lat"].notna() & df["lon"].notna()
    sub = df[valid_coords].copy()

    coords = sub[["lat", "lon"]].drop_duplicates()
    coord_to_cell: dict[tuple[float, float], str] = {}
    for r in coords.itertuples(index=False):
        try:
            coord_to_cell[(r.lat, r.lon)] = h3.latlng_to_cell(float(r.lat), float(r.lon), h3_resolution)
        except Exception:
            continue

    cells = [coord_to_cell.get((la, lo)) for la, lo in zip(sub["lat"], sub["lon"])]
    in_mask = pd.Series(
        [(plat, c) in mask if c else False for plat, c in zip(sub["platform"], cells)],
        index=sub.index,
    )

    if "processing_stream" in sub.columns:
        is_nrt = sub["processing_stream"].astype(str).isin(["NRT", "nrt"])
    else:
        is_nrt = pd.Series(False, index=sub.index)
    is_sp = ~is_nrt

    fire_type_str = (
        sub["fire_type"].astype(str).str.strip().str.replace(".0", "", regex=False)
        if "fire_type" in sub.columns
        else pd.Series("", index=sub.index)
    )

    is_type0 = is_sp & (fire_type_str == "0")
    is_static = is_sp & fire_type_str.isin(["2", "3"])

    tot_nrt = int(is_nrt.sum())
    nrt_flagged = int((is_nrt & in_mask).sum())
    nrt_share = float(nrt_flagged / tot_nrt) if tot_nrt > 0 else 0.0

    tot_type0 = int(is_type0.sum())
    type0_in_mask = int((is_type0 & in_mask).sum())
    type0_share = float(type0_in_mask / tot_type0) if tot_type0 > 0 else 0.0

    tot_static = int(is_static.sum())
    static_in_mask = int((is_static & in_mask).sum())
    static_share = float(static_in_mask / tot_static) if tot_static > 0 else 0.0

    return {
        "total_nrt": tot_nrt,
        "nrt_flagged": nrt_flagged,
        "nrt_flagged_share": round(nrt_share, 4),
        "total_archive_type0": tot_type0,
        "archive_type0_in_mask": type0_in_mask,
        "archive_type0_share": round(type0_share, 4),
        "total_archive_static": tot_static,
        "archive_static_in_mask": static_in_mask,
        "archive_static_share": round(static_share, 4),
    }


def save_static_mask(mask: set[tuple[str, str]], data_dir: Path) -> Path:
    """Save static source mask to data/staging/static_source_mask.json."""
    p = data_dir / "staging" / "static_source_mask.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump([list(x) for x in sorted(mask)], f, indent=2)
    return p


def load_static_mask(data_dir: Path) -> set[tuple[str, str]]:
    """Load static source mask from data/staging/static_source_mask.json."""
    p = data_dir / "staging" / "static_source_mask.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {tuple(x) for x in data}
        except Exception:
            pass
    return set()

