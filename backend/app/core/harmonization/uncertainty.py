"""Uncertainty estimation for TerraFlare harmonization using block bootstrap.

Implements stationary block bootstrap over time blocks (e.g. 7-day blocks)
to compute empirical prediction and credible intervals for harmonized active-fire counts.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from app.settings import settings
from app.shared.config_loader import get_harmonization_config


def get_uncertainty_config() -> dict[str, Any]:
    """Read bootstrap and interval parameters from harmonization.yaml."""
    cfg = get_harmonization_config()
    b_cfg = cfg.get("bootstrap", {})
    return {
        "block_days": int(b_cfg.get("block_days", 7)),
        "reps": int(b_cfg.get("reps", 500)),
        "interval_level": float(b_cfg.get("interval_level", 0.9)),
    }


def compute_block_bootstrap_ratios(
    overlap_df: pd.DataFrame,
    num_col: str = "viirs_count",
    denom_col: str = "modis_count",
    date_col: str = "date",
    block_days: int = 7,
    reps: int = 500,
    interval_level: float = 0.9,
    random_seed: int = 42,
) -> dict[str, float]:
    """Compute block bootstrap confidence interval for ratio sum(num) / sum(denom).

    Time series is chunked into contiguous blocks of `block_days`.
    Blocks are resampled with replacement `reps` times to compute empirical quantiles.

    Returns dict with:
        mean_ratio, lower_ratio, upper_ratio, rel_lower_err, rel_upper_err
    """
    if overlap_df.empty or num_col not in overlap_df.columns or denom_col not in overlap_df.columns:
        return {
            "mean_ratio": 1.0,
            "lower_ratio": 0.8,
            "upper_ratio": 1.2,
            "rel_lower_err": 0.2,
            "rel_upper_err": 0.2,
            "interval_level": interval_level,
        }

    df = overlap_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    min_date = df[date_col].min()

    # Assign block index based on days elapsed from min_date
    df["_block_idx"] = ((df[date_col] - min_date).dt.days // block_days).astype(int)

    # Pre-aggregate by block to make resampling fast
    block_sums = df.groupby("_block_idx")[[num_col, denom_col]].sum().reset_index()
    n_blocks = len(block_sums)

    if n_blocks == 0 or block_sums[denom_col].sum() == 0:
        return {
            "mean_ratio": 1.0,
            "lower_ratio": 0.8,
            "upper_ratio": 1.2,
            "rel_lower_err": 0.2,
            "rel_upper_err": 0.2,
            "interval_level": interval_level,
        }

    rng = np.random.default_rng(random_seed)
    sampled_indices = rng.choice(n_blocks, size=(reps, n_blocks), replace=True)

    nums = block_sums[num_col].to_numpy()
    denoms = block_sums[denom_col].to_numpy()

    # Resampled sums
    boot_nums = nums[sampled_indices].sum(axis=1)
    boot_denoms = denoms[sampled_indices].sum(axis=1)

    # Avoid zero division
    valid_reps = boot_denoms > 0
    if not np.any(valid_reps):
        base_ratio = float(nums.sum() / max(1.0, denoms.sum()))
        return {
            "mean_ratio": base_ratio,
            "lower_ratio": base_ratio * 0.8,
            "upper_ratio": base_ratio * 1.2,
            "rel_lower_err": 0.2,
            "rel_upper_err": 0.2,
            "interval_level": interval_level,
        }

    boot_ratios = boot_nums[valid_reps] / boot_denoms[valid_reps]

    alpha = (1.0 - interval_level) / 2.0
    lower_pct = alpha * 100.0
    upper_pct = (1.0 - alpha) * 100.0

    lower_ratio = float(np.percentile(boot_ratios, lower_pct))
    upper_ratio = float(np.percentile(boot_ratios, upper_pct))
    mean_ratio = float(np.mean(boot_ratios))

    # Relative error bounds around the mean
    rel_lower = max(0.0, (mean_ratio - lower_ratio) / mean_ratio) if mean_ratio > 0 else 0.2
    rel_upper = max(0.0, (upper_ratio - mean_ratio) / mean_ratio) if mean_ratio > 0 else 0.2

    return {
        "mean_ratio": mean_ratio,
        "lower_ratio": lower_ratio,
        "upper_ratio": upper_ratio,
        "rel_lower_err": rel_lower,
        "rel_upper_err": rel_upper,
        "interval_level": interval_level,
    }


def compute_prediction_interval(
    estimated_val: float,
    rel_lower_err: float = 0.2,
    rel_upper_err: float = 0.2,
) -> tuple[float, float]:
    """Compute (harmonized_lower, harmonized_upper) for an estimated value."""
    val = float(estimated_val)
    if val <= 0:
        return 0.0, 0.0
    lower = max(0.0, val * (1.0 - rel_lower_err))
    upper = val * (1.0 + rel_upper_err)
    return round(lower, 4), round(upper, 4)


def compute_observed_interval(
    observed_val: float,
    interval_level: float = 0.9,
) -> tuple[float, float]:
    """Return confidence interval for directly observed counts.

    Rule (Task 7b): For value_type 'observed', harmonized_lower = harmonized_upper = observed_val.
    The Poisson interval is removed. Uncertainty intervals apply strictly to estimated values
    and quantify calibration parameter uncertainty (via block bootstrap), not Poisson process noise.
    """
    val = float(observed_val)
    if val <= 0:
        return 0.0, 0.0
    return round(val, 4), round(val, 4)


def get_size_dependent_uncertainty_config() -> dict[str, Any]:
    """Read size_dependent_uncertainty config from harmonization.yaml."""
    cfg = get_harmonization_config()
    return cfg.get("size_dependent_uncertainty", {})


def interval_for(expected_count: float) -> tuple[float | None, float | None, str]:
    """Return (lower_bound_rel, upper_bound_rel, reliability_label) for an expected count.

    Rule (Task 7f Item 3, Task 7g Item 3):
    - When expected_count <= 0 or below the very_small threshold (< 10),
      return no interval (None, None) and reliability 'insufficient'.
    - For expected_count >= 10:
      - Class bins by expected monthly count configured in harmonization.yaml.
      - Adds bridge uncertainty term to relative lower and upper bounds.
      - Evaluates half-width against configured thresholds to assign reliability:
        'high', 'medium', or 'low'.
    """
    val = float(expected_count)
    u_cfg = get_size_dependent_uncertainty_config()
    bins = u_cfg.get("class_bins", [])

    # Identify very_small threshold (defaults to 10.0 if not configured)
    very_small_th = 10.0
    for b in bins:
        if b.get("name") == "very_small":
            very_small_th = float(b.get("max_expected", 10.0))
            break

    if val <= 0.0 or val < very_small_th:
        return None, None, "insufficient"

    bridge_term = float(u_cfg.get("bridge_uncertainty_rel", 0.0184))
    thresh = u_cfg.get("reliability_thresholds", {})
    high_th = float(thresh.get("high_max_rel_halfwidth", 0.20))
    med_th = float(thresh.get("medium_max_rel_halfwidth", 0.45))

    matched_bin = None
    for b in bins:
        if b.get("name") == "very_small":
            continue
        min_v = float(b.get("min_expected", 0))
        max_v = float(b.get("max_expected", float("inf")))
        if min_v <= val < max_v:
            matched_bin = b
            break

    if matched_bin is None and bins:
        matched_bin = bins[-1]

    if matched_bin:
        base_lower = float(matched_bin.get("rel_lower", 0.5))
        base_upper = float(matched_bin.get("rel_upper", 1.5))
    else:
        if val < 50:
            base_lower, base_upper = 0.717, 6.244
        elif val < 250:
            base_lower, base_upper = 0.598, 4.401
        elif val < 1000:
            base_lower, base_upper = 0.512, 2.728
        elif val < 5000:
            base_lower, base_upper = 0.440, 1.167
        else:
            base_lower, base_upper = 0.125, 0.142

    total_lower = round(base_lower + bridge_term, 4)
    total_upper = round(base_upper + bridge_term, 4)
    half_width = (total_lower + total_upper) / 2.0

    if half_width <= high_th:
        reliability = "high"
    elif half_width <= med_th:
        reliability = "medium"
    else:
        reliability = "low"

    return total_lower, total_upper, reliability


