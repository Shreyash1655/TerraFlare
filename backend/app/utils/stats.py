"""Statistical helpers used by TerraFlare advanced features."""

from __future__ import annotations

import numpy as np
from scipy.stats import kendalltau, theilslopes


def bootstrap_median_diff(
    baseline,
    recent,
    n_bootstrap=1000,
    seed=42,
    ci_level=0.95,
):
    """Estimate recent median minus baseline median with bootstrap CI."""

    a = np.asarray(baseline, dtype=float)
    b = np.asarray(recent, dtype=float)

    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]

    if len(a) == 0 or len(b) == 0:
        return None, None, None

    estimate = float(np.median(b) - np.median(a))

    rng = np.random.default_rng(seed)

    samples = np.empty(n_bootstrap)

    for i in range(n_bootstrap):
        sample_a = rng.choice(a, size=len(a), replace=True)
        sample_b = rng.choice(b, size=len(b), replace=True)

        samples[i] = np.median(sample_b) - np.median(sample_a)

    alpha = (1.0 - ci_level) / 2.0

    lower = float(np.quantile(samples, alpha))
    upper = float(np.quantile(samples, 1.0 - alpha))

    return estimate, lower, upper


def theil_sen(x, y):
    """Return Theil-Sen slope and Kendall trend p-value."""

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]

    if len(x) < 3:
        return None, None

    slope = float(theilslopes(y, x).slope)
    p_value = float(kendalltau(x, y).pvalue)

    return slope, p_value


def theil_sen_slope(x, y):
    """Return only the Theil-Sen slope."""

    slope, _ = theil_sen(x, y)
    return slope if slope is not None else np.nan


def robust_z(value, baseline):
    """Calculate robust z-score using median and MAD."""

    values = np.asarray(baseline, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0 or not np.isfinite(value):
        return None

    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))

    if mad == 0:
        if value == median:
            return 0.0

        # Avoid division by zero when the baseline has zero MAD.
        scale = float(np.std(values))

        if scale == 0:
            return float(
                np.sign(value - median) * 10.0
            )

        return float((value - median) / scale)

    return float((value - median) / (1.4826 * mad))


def percentile_rank(value, baseline):
    """Return the percentage of baseline values at or below value."""

    values = np.asarray(baseline, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return None

    return float(np.mean(values <= value) * 100.0)