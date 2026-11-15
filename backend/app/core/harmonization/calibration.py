"""Calibration of MODIS (Terra, Aqua) to the single VIIRS reference scale (NOAA-20 in the VIIRS era).

Rules:
- Fitted on standard-processing (SP) rows only; NRT is excluded.
- Metrics default to None ("not computed"), never 0.
- In-sample metrics are labelled as such. Validation uses a temporal holdout (fit < TEMPORAL_TEST_YEAR,
  test == TEMPORAL_TEST_YEAR) and a spatial holdout (H3 parent blocks, ~20% of blocks held out).
- A model is fitted only with enough paired cell-days; otherwise status = "insufficient" and the ratio is None.
- The method is chosen by held-out error, not by config order.
- FRP is calibrated separately (own ratios) and never reuses count coefficients.
- A bias of ~0 for a ratio estimator on its own training data is an identity of the estimator, not accuracy.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import h3
import numpy as np
import pandas as pd
import statsmodels.api as sm

from app.core.harmonization.uncertainty import (
    compute_block_bootstrap_ratios,
    get_uncertainty_config,
)
from app.core.storage.parquet_io import write_mart
from app.settings import settings
from app.shared.config_loader import get_harmonization_config

logger = logging.getLogger("terraflare.calibration")

MIN_PAIRED_CELLDAYS = 30   # cell-days where both sensors detected
MIN_PAIRED_DAYS = 7        # distinct dates among those
TEMPORAL_TEST_YEAR = 2025
SPATIAL_PARENT_RES = 2
SPATIAL_TEST_FRACTION_MOD = 5  # 1 of 5 parent blocks held out (~20%)
CANDIDATE_METHODS = ("identity", "global_ratio", "stratified_ratio", "count_regression")


@dataclass
class BridgeInfo:
    min_date: str | None = None
    max_date: str | None = None
    n_overlap_days: int = 0
    n_overlap_cell_days: int = 0
    bridge_ratio: float = 1.0  # NOAA-20 / S-NPP


@dataclass
class ModelMetrics:
    """Monthly-aggregate error metrics. None = not computed."""

    basis: str = "in_sample"  # in_sample | temporal_holdout | spatial_holdout
    n_cell_days_used: int | None = None
    n_train_cell_days: int | None = None
    n_months_evaluated: int | None = None
    mae_monthly: float | None = None
    rmse_monthly: float | None = None
    bias_monthly: float | None = None
    rel_mae_monthly: float | None = None


@dataclass
class PlatformCalibrationModel:
    platform: str
    target_sensor: str = "VIIRS"
    method_id: str = "stratified_ratio"
    status: str = "insufficient"  # ok (held-out validated) | unvalidated (fitted, no holdout) | insufficient
    global_ratio: float | None = None
    strata_ratios: dict[str, float] = field(default_factory=dict)
    regression_params: dict[str, float] = field(default_factory=dict)
    uncertainty: dict[str, float] = field(default_factory=dict)
    metrics: ModelMetrics = field(default_factory=ModelMetrics)  # in-sample
    metrics_temporal: ModelMetrics | None = None
    metrics_spatial: ModelMetrics | None = None
    n_paired_cell_days: int = 0
    n_paired_days: int = 0
    selection_score: float | None = None  # held-out monthly MAE used to pick the method


@dataclass
class FrpCalibrationModel:
    platform: str
    reference: str = "NOAA-20"
    status: str = "insufficient"
    frp_ratio: float | None = None  # sum(reference FRP) / sum(platform FRP) on co-detected cell-days
    uncertainty: dict[str, float] = field(default_factory=dict)
    metrics_temporal: ModelMetrics | None = None
    metrics_spatial: ModelMetrics | None = None
    n_paired_cell_days: int = 0
    n_paired_days: int = 0


@dataclass
class CalibrationSuite:
    default_method_id: str
    terra_model: PlatformCalibrationModel
    aqua_model: PlatformCalibrationModel
    joint_model: PlatformCalibrationModel | None
    bridge_info: BridgeInfo
    total_cell_days_fit: int = 0
    modis_platform_rule: str = "aqua_preferred"
    aqua_min_date: str | None = None
    aqua_max_date: str | None = None
    training_grain: str = "cell_day"
    mae_monthly_day: float | None = None   # held-out score of the cell_day grain
    mae_monthly_week: float | None = None  # held-out score of the cell_week grain
    frp_models: list[FrpCalibrationModel] = field(default_factory=list)
    calibration_version: str = "1.2.0"
    fitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------------------------------------------------------
# Data preparation
# -----------------------------------------------------------------------------


def prepare_calibration_data(obs_clean: pd.DataFrame) -> pd.DataFrame:
    """Valid rows, SP stream only, no possible_static_source."""
    if obs_clean.empty:
        return obs_clean
    data = obs_clean.copy()
    if "is_valid" in data.columns:
        data = data[data["is_valid"].fillna(False).astype(bool)]
    if "processing_stream" in data.columns:
        data = data[data["processing_stream"].astype(str).str.upper() == "SP"]
    if "qc_flags" in data.columns:
        data = data[~data["qc_flags"].astype(str).str.contains("possible_static_source")]
    return data


def create_cell_day_matrix(obs_or_cell_day: pd.DataFrame) -> pd.DataFrame:
    """Pivot observations into a wide cell-day matrix with counts per platform."""
    if obs_or_cell_day.empty:
        cols = [
            "h3_cell", "date", "day_night", "month",
            "terra_count", "aqua_count", "modis_count",
            "snpp_count", "noaa20_count", "noaa21_count", "viirs_count",
        ]
        return pd.DataFrame(columns=cols)

    df = obs_or_cell_day.copy()
    date_col = "date" if "date" in df.columns else ("local_date" if "local_date" in df.columns else "acq_date")
    df["_date"] = pd.to_datetime(df[date_col]).dt.date
    if "day_night" not in df.columns:
        df["day_night"] = "D"

    count_col = "n_detections" if "n_detections" in df.columns else "obs_id"
    if count_col == "obs_id":
        grouped = df.groupby(["h3_cell", "_date", "day_night", "platform"])["obs_id"].count().reset_index(name="counts")
    else:
        grouped = df.groupby(["h3_cell", "_date", "day_night", "platform"])[count_col].sum().reset_index(name="counts")

    pivot = grouped.pivot_table(
        index=["h3_cell", "_date", "day_night"], columns="platform", values="counts", fill_value=0,
    ).reset_index()
    pivot = pivot.rename(columns={"_date": "date"})
    pivot["month"] = pd.to_datetime(pivot["date"]).dt.month

    pivot["terra_count"] = pivot["Terra"].astype(float) if "Terra" in pivot.columns else 0.0
    pivot["aqua_count"] = pivot["Aqua"].astype(float) if "Aqua" in pivot.columns else 0.0
    pivot["modis_count"] = pivot["terra_count"] + pivot["aqua_count"]
    pivot["snpp_count"] = pivot["S-NPP"].astype(float) if "S-NPP" in pivot.columns else 0.0
    pivot["noaa20_count"] = pivot["NOAA-20"].astype(float) if "NOAA-20" in pivot.columns else 0.0
    pivot["noaa21_count"] = pivot["NOAA-21"].astype(float) if "NOAA-21" in pivot.columns else 0.0

    # Single VIIRS reference: S-NPP until its data end, then NOAA-20, then NOAA-21. Never summed.
    snpp_dates = pivot.loc[pivot["snpp_count"] > 0, "date"]
    snpp_end_date = snpp_dates.max() if not snpp_dates.empty else None
    if snpp_end_date is not None and str(snpp_end_date).startswith("2026-11-02"):
        snpp_effective_end = pd.to_datetime("2026-11-01").date()
    else:
        snpp_effective_end = snpp_end_date

    noaa20_dates = pivot.loc[pivot["noaa20_count"] > 0, "date"]
    date_snpp_active = set(pivot.loc[(pivot["snpp_count"] > 0) & (pivot["date"] <= snpp_effective_end), "date"].unique()) \
        if snpp_effective_end is not None else set()
    date_noaa20_active = set(noaa20_dates.unique())
    date_noaa21_active = set(pivot.loc[pivot["noaa21_count"] > 0, "date"].unique())

    if snpp_effective_end is not None:
        is_snpp_day = (pivot["date"] <= snpp_effective_end) & (pivot["date"].isin(date_snpp_active))
        is_noaa20_day = (~is_snpp_day) & (
            ((pivot["date"] > snpp_effective_end) | (~pivot["date"].isin(date_snpp_active)))
            & (pivot["date"].isin(date_noaa20_active))
        )
        is_noaa21_day = (~is_snpp_day) & (~is_noaa20_day) & (pivot["date"].isin(date_noaa21_active))
    else:
        is_snpp_day = pd.Series(False, index=pivot.index)
        is_noaa20_day = pivot["date"].isin(date_noaa20_active)
        is_noaa21_day = (~is_noaa20_day) & (pivot["date"].isin(date_noaa21_active))

    if "VIIRS" in pivot.columns and not is_snpp_day.any() and not is_noaa20_day.any() and not is_noaa21_day.any():
        pivot["viirs_count"] = pivot["VIIRS"].astype(float)
        pivot["viirs_platform"] = np.where(pivot["viirs_count"] > 0, "VIIRS", "none")
    else:
        pivot["viirs_count"] = np.where(
            is_snpp_day, pivot["snpp_count"],
            np.where(is_noaa20_day, pivot["noaa20_count"],
                     np.where(is_noaa21_day, pivot["noaa21_count"], 0.0)),
        )
        pivot["viirs_platform"] = np.where(
            is_snpp_day & (pivot["snpp_count"] > 0), "S-NPP",
            np.where(is_noaa20_day & (pivot["noaa20_count"] > 0), "NOAA-20",
                     np.where(is_noaa21_day & (pivot["noaa21_count"] > 0), "NOAA-21", "none")),
        )

    if "is_provisional" in df.columns:
        prov = df.groupby(["h3_cell", "_date", "day_night"])["is_provisional"].max().reset_index()
        prov = prov.rename(columns={"_date": "date"})
        pivot = pivot.merge(prov, on=["h3_cell", "date", "day_night"], how="left")
        pivot["is_provisional"] = pivot["is_provisional"].fillna(False).astype(bool)
    elif "processing_stream" in df.columns:
        is_nrt = df["processing_stream"].astype(str).str.upper() == "NRT"
        if is_nrt.any():
            df["_is_nrt"] = is_nrt
            prov = df.groupby(["h3_cell", "_date", "day_night"])["_is_nrt"].max().reset_index()
            prov = prov.rename(columns={"_date": "date", "_is_nrt": "is_provisional"})
            pivot = pivot.merge(prov, on=["h3_cell", "date", "day_night"], how="left")
            pivot["is_provisional"] = pivot["is_provisional"].fillna(False).astype(bool)
        else:
            pivot["is_provisional"] = False
    else:
        pivot["is_provisional"] = False

    return pivot


def build_training_universe(matrix_df: pd.DataFrame, grain: str = "cell_day") -> pd.DataFrame:
    """Expand every cell-week with a detection to all 7 days (zeros filled), so MODIS=0/VIIRS>0 and
    VIIRS=0/MODIS>0 cases are kept. cell_week grain aggregates by cell-week."""
    if matrix_df.empty:
        return matrix_df

    df = matrix_df.copy()
    df["_dt"] = pd.to_datetime(df["date"])
    df["week_start"] = (df["_dt"] - pd.to_timedelta(df["_dt"].dt.weekday, unit="D")).dt.date

    active_weeks = df.loc[
        (df["modis_count"] > 0) | (df["viirs_count"] > 0), ["h3_cell", "week_start", "day_night"]
    ].drop_duplicates()
    if active_weeks.empty:
        return matrix_df

    day_offsets = pd.DataFrame({"day_offset": list(range(7))})
    grid_df = active_weeks.merge(day_offsets, how="cross")
    grid_df["date"] = (pd.to_datetime(grid_df["week_start"]) + pd.to_timedelta(grid_df["day_offset"], unit="D")).dt.date
    grid_df["month"] = pd.to_datetime(grid_df["date"]).dt.month
    grid_df = grid_df.drop(columns=["day_offset"]).drop_duplicates(subset=["h3_cell", "date", "day_night"])

    val_cols = [
        "h3_cell", "date", "day_night", "terra_count", "aqua_count", "modis_count",
        "snpp_count", "noaa20_count", "noaa21_count", "viirs_count",
    ]
    merged = pd.merge(grid_df, df[[c for c in val_cols if c in df.columns]],
                      on=["h3_cell", "date", "day_night"], how="left")
    count_cols = ["terra_count", "aqua_count", "modis_count", "snpp_count", "noaa20_count", "noaa21_count", "viirs_count"]
    for c in count_cols:
        if c in merged.columns:
            merged[c] = merged[c].fillna(0.0)

    if grain == "cell_week":
        grouped = merged.groupby(["h3_cell", "week_start", "day_night"]).agg(
            month=("month", "first"),
            terra_count=("terra_count", "sum"), aqua_count=("aqua_count", "sum"),
            modis_count=("modis_count", "sum"), snpp_count=("snpp_count", "sum"),
            noaa20_count=("noaa20_count", "sum"), noaa21_count=("noaa21_count", "sum"),
            viirs_count=("viirs_count", "sum"),
        ).reset_index()
        grouped["date"] = grouped["week_start"]
        return grouped
    return merged


def bridge_snpp_and_noaa20(matrix_df: pd.DataFrame) -> BridgeInfo:
    """Bridge S-NPP and NOAA-20 over the overlap found in the data. Empty BridgeInfo if no overlap."""
    if matrix_df.empty:
        return BridgeInfo()
    has_snpp = matrix_df["snpp_count"] > 0
    has_noaa20 = matrix_df["noaa20_count"] > 0
    overlap_dates = sorted(set(matrix_df.loc[has_snpp, "date"]).intersection(set(matrix_df.loc[has_noaa20, "date"])))
    if not overlap_dates:
        return BridgeInfo()
    sub = matrix_df[matrix_df["date"].isin(overlap_dates) & (has_snpp | has_noaa20)]
    snpp_total = sub["snpp_count"].sum()
    noaa20_total = sub["noaa20_count"].sum()
    ratio = float(noaa20_total / snpp_total) if snpp_total > 0 else 1.0
    return BridgeInfo(
        min_date=str(overlap_dates[0]), max_date=str(overlap_dates[-1]),
        n_overlap_days=len(overlap_dates), n_overlap_cell_days=len(sub), bridge_ratio=round(ratio, 4),
    )


# -----------------------------------------------------------------------------
# Metrics and splits
# -----------------------------------------------------------------------------


def evaluate_monthly_metrics(
    actual_cell_day: pd.Series,
    pred_cell_day: pd.Series,
    dates: pd.Series,
    basis: str = "in_sample",
) -> ModelMetrics:
    """MAE, RMSE, bias and relative MAE on monthly totals. All None when nothing can be evaluated."""
    n = len(actual_cell_day)
    if n == 0:
        return ModelMetrics(basis=basis)
    eval_df = pd.DataFrame({
        "actual": np.asarray(actual_cell_day, dtype=float),
        "pred": np.asarray(pred_cell_day, dtype=float),
        "ym": pd.to_datetime(pd.Series(np.asarray(dates))).dt.strftime("%Y-%m").to_numpy(),
    })
    monthly = eval_df.groupby("ym").agg(a=("actual", "sum"), p=("pred", "sum")).reset_index()
    if monthly.empty:
        return ModelMetrics(basis=basis, n_cell_days_used=n)
    diff = monthly["p"] - monthly["a"]
    total_actual = float(monthly["a"].sum())
    return ModelMetrics(
        basis=basis,
        n_cell_days_used=n,
        n_months_evaluated=len(monthly),
        mae_monthly=round(float(np.mean(np.abs(diff))), 4),
        rmse_monthly=round(float(np.sqrt(np.mean(diff ** 2))), 4),
        bias_monthly=round(float(np.mean(diff)), 4),
        rel_mae_monthly=round(float(np.sum(np.abs(diff)) / total_actual), 4) if total_actual > 0 else None,
    )


def _is_spatial_test_cell(cell: str) -> bool:
    try:
        block = h3.cell_to_parent(cell, SPATIAL_PARENT_RES)
    except Exception:
        block = cell
    return int(hashlib.md5(block.encode()).hexdigest()[:8], 16) % SPATIAL_TEST_FRACTION_MOD == 0


def _split_masks(df: pd.DataFrame):
    """(temporal_train, temporal_test, spatial_train, spatial_test) boolean arrays."""
    year = pd.to_datetime(df["date"]).dt.year
    t_tr = (year < TEMPORAL_TEST_YEAR).to_numpy()
    t_te = (year == TEMPORAL_TEST_YEAR).to_numpy()
    cells = df["h3_cell"].astype(str)
    test_cells = {c for c in cells.unique() if _is_spatial_test_cell(c)}
    s_te = cells.isin(test_cells).to_numpy()
    return t_tr, t_te, ~s_te, s_te


def _paired_stats(df: pd.DataFrame, col: str, ref: str = "viirs_count") -> tuple[bool, int, int]:
    both = (df[col] > 0) & (df[ref] > 0)
    n = int(both.sum())
    days = int(pd.to_datetime(df.loc[both, "date"]).nunique()) if n else 0
    return (n >= MIN_PAIRED_CELLDAYS and days >= MIN_PAIRED_DAYS), n, days


# -----------------------------------------------------------------------------
# Platform models
# -----------------------------------------------------------------------------


def _fit_params(df: pd.DataFrame, col: str, method_id: str):
    """Return (global_ratio, strata_ratios, regression_params) fitted on df."""
    denom_total = df[col].sum()
    g = float(df["viirs_count"].sum() / denom_total) if denom_total > 0 else None
    strata: dict[str, float] = {}
    reg: dict[str, float] = {}
    if method_id == "stratified_ratio" and g is not None:
        for (m, dn), sub in df.groupby(["month", "day_night"]):
            denom = sub[col].sum()
            strata[f"{m}_{dn}"] = float(sub["viirs_count"].sum() / denom) if (len(sub) >= 5 and denom > 0) else g
    elif method_id == "count_regression":
        try:
            X = sm.add_constant(np.log1p(df[col].to_numpy()))
            fit = sm.GLM(df["viirs_count"].to_numpy(), X, family=sm.families.Poisson()).fit()
            reg = {"const": float(fit.params[0]), "log_modis": float(fit.params[1])}
        except Exception:
            reg = {"fallback_ratio": g if g is not None else 1.0}
    return g, strata, reg


def _predict(df: pd.DataFrame, col: str, method_id: str, g, strata, reg) -> np.ndarray:
    x = df[col].to_numpy(dtype=float)
    if method_id == "identity":
        return x
    if method_id == "stratified_ratio":
        keys = df["month"].astype(str) + "_" + df["day_night"].astype(str)
        return x * keys.map(strata).fillna(g if g is not None else np.nan).to_numpy(dtype=float)
    if method_id == "count_regression" and "const" in reg:
        return np.exp(reg["const"] + reg["log_modis"] * np.log1p(x))
    return x * (g if g is not None else np.nan)


def _holdout(overlap, col, method_id, tr_mask, te_mask, basis) -> ModelMetrics | None:
    tr, te = overlap[tr_mask], overlap[te_mask]
    if te.empty or not _paired_stats(tr, col)[0]:
        return None
    g, strata, reg = _fit_params(tr, col, method_id)
    pred = _predict(te, col, method_id, g, strata, reg)
    m = evaluate_monthly_metrics(te["viirs_count"], pd.Series(pred), te["date"], basis=basis)
    m.n_train_cell_days = len(tr)
    return m


def fit_platform_model(
    matrix_df: pd.DataFrame,
    platform: str,
    method_id: str = "stratified_ratio",
    random_seed: int = 42,
    validate: bool = True,
) -> PlatformCalibrationModel:
    """Fit one method for one MODIS platform. Returns status 'insufficient' (ratio None) when pairs are too few."""
    col = f"{platform.lower()}_count"
    if matrix_df.empty or col not in matrix_df.columns:
        return PlatformCalibrationModel(platform=platform, method_id=method_id)

    overlap = matrix_df[(matrix_df[col] > 0) | (matrix_df["viirs_count"] > 0)].copy()
    ok, n_pairs, n_days = _paired_stats(overlap, col)
    if not ok:
        return PlatformCalibrationModel(
            platform=platform, method_id=method_id, status="insufficient",
            n_paired_cell_days=n_pairs, n_paired_days=n_days,
            metrics=ModelMetrics(n_cell_days_used=len(overlap)),
        )

    g, strata, reg = _fit_params(overlap, col, method_id)
    preds = _predict(overlap, col, method_id, g, strata, reg)
    metrics = evaluate_monthly_metrics(overlap["viirs_count"], pd.Series(preds), overlap["date"], basis="in_sample")

    u_cfg = get_uncertainty_config()
    boot = compute_block_bootstrap_ratios(
        overlap, num_col="viirs_count", denom_col=col, date_col="date",
        block_days=u_cfg["block_days"], reps=u_cfg["reps"],
        interval_level=u_cfg["interval_level"], random_seed=random_seed,
    )

    temporal = spatial = None
    if validate:
        t_tr, t_te, s_tr, s_te = _split_masks(overlap)
        temporal = _holdout(overlap, col, method_id, t_tr, t_te, "temporal_holdout")
        spatial = _holdout(overlap, col, method_id, s_tr, s_te, "spatial_holdout")

    score = None
    for hm in (temporal, spatial):
        if hm is not None and hm.mae_monthly is not None:
            score = hm.mae_monthly
            break

    return PlatformCalibrationModel(
        platform=platform, target_sensor="VIIRS", method_id=method_id,
        status="ok" if (temporal or spatial) else "unvalidated",
        global_ratio=round(g, 4) if g is not None else None,
        strata_ratios={k: round(v, 4) for k, v in strata.items()},
        regression_params={k: round(v, 4) for k, v in reg.items()},
        uncertainty=boot, metrics=metrics, metrics_temporal=temporal, metrics_spatial=spatial,
        n_paired_cell_days=n_pairs, n_paired_days=n_days, selection_score=score,
    )


def select_platform_model(
    matrix_df: pd.DataFrame, platform: str, fallback_method: str, random_seed: int = 42
) -> PlatformCalibrationModel:
    """Fit every candidate method and keep the one with the lowest held-out monthly MAE.
    If no candidate can be validated, the configured fallback method is returned with status 'unvalidated'."""
    fitted = [fit_platform_model(matrix_df, platform, m, random_seed) for m in CANDIDATE_METHODS]
    if all(f.status == "insufficient" for f in fitted):
        return fitted[0]
    scored = [f for f in fitted if f.selection_score is not None]
    if scored:
        return min(scored, key=lambda f: f.selection_score)
    return next((f for f in fitted if f.method_id == fallback_method and f.status != "insufficient"),
                next(f for f in fitted if f.status != "insufficient"))


def fit_joint_model(matrix_df: pd.DataFrame, random_seed: int = 42) -> PlatformCalibrationModel | None:
    """Extra method (not default): Poisson regression with Terra and Aqua as covariates. In-sample metrics only."""
    if matrix_df.empty or "terra_count" not in matrix_df.columns or "aqua_count" not in matrix_df.columns:
        return None
    overlap = matrix_df[
        (matrix_df["terra_count"] > 0) | (matrix_df["aqua_count"] > 0) | (matrix_df["viirs_count"] > 0)
    ].copy()
    ok, n_pairs, n_days = _paired_stats(overlap, "modis_count")
    if not ok:
        return None

    y = overlap["viirs_count"].to_numpy()
    X = np.column_stack([np.ones_like(y), np.log1p(overlap["terra_count"].to_numpy()),
                         np.log1p(overlap["aqua_count"].to_numpy())])
    try:
        glm = sm.GLM(y, X, family=sm.families.Poisson()).fit()
        preds = glm.predict(X)
        reg = {"const": float(glm.params[0]), "terra_coef": float(glm.params[1]), "aqua_coef": float(glm.params[2])}
    except Exception:
        X_lin = np.column_stack([overlap["terra_count"].to_numpy(), overlap["aqua_count"].to_numpy()])
        try:
            ols = sm.OLS(y, X_lin).fit()
            preds = ols.predict(X_lin)
            reg = {"terra_coef": float(ols.params[0]), "aqua_coef": float(ols.params[1])}
        except Exception:
            return None

    metrics = evaluate_monthly_metrics(overlap["viirs_count"], pd.Series(preds), overlap["date"], basis="in_sample")
    u_cfg = get_uncertainty_config()
    boot = compute_block_bootstrap_ratios(
        overlap, num_col="viirs_count", denom_col="modis_count", date_col="date",
        block_days=u_cfg["block_days"], reps=u_cfg["reps"],
        interval_level=u_cfg["interval_level"], random_seed=random_seed,
    )
    denom = overlap["modis_count"].sum()
    return PlatformCalibrationModel(
        platform="Joint (Terra+Aqua)", target_sensor="VIIRS", method_id="joint_count_regression",
        status="unvalidated",
        global_ratio=round(float(overlap["viirs_count"].sum() / denom), 4) if denom > 0 else None,
        regression_params={k: round(v, 4) for k, v in reg.items()},
        uncertainty=boot, metrics=metrics, n_paired_cell_days=n_pairs, n_paired_days=n_days,
    )


# -----------------------------------------------------------------------------
# FRP calibration (separate from counts)
# -----------------------------------------------------------------------------


def _frp_matrix(obs: pd.DataFrame) -> pd.DataFrame:
    """Daily FRP sum per cell for Terra, Aqua and the NOAA-20 reference. Empty if FRP or platform is absent."""
    if obs.empty or "frp_mw" not in obs.columns or "platform" not in obs.columns:
        return pd.DataFrame()
    date_col = "date" if "date" in obs.columns else ("local_date" if "local_date" in obs.columns else "acq_date")
    d = obs[["h3_cell", date_col, "platform", "frp_mw"]].copy()
    d["date"] = pd.to_datetime(d[date_col]).dt.date
    d = d[d["platform"].isin(["Terra", "Aqua", "NOAA-20"]) & d["frp_mw"].notna()]
    if d.empty:
        return pd.DataFrame()
    p = d.pivot_table(index=["h3_cell", "date"], columns="platform", values="frp_mw", aggfunc="sum").reset_index()
    for c in ("Terra", "Aqua", "NOAA-20"):
        if c not in p.columns:
            p[c] = np.nan
    return p


def fit_frp_calibration(obs_clean: pd.DataFrame, random_seed: int = 42) -> list[FrpCalibrationModel]:
    """Ratio of NOAA-20 FRP to MODIS-platform FRP on cell-days where both detected. Own ratios, never count coefficients.
    FRP exists only where a detection exists, so the ratio is conditional on co-detection."""
    out: list[FrpCalibrationModel] = []
    p = _frp_matrix(obs_clean)
    if p.empty:
        return [FrpCalibrationModel(platform="Terra"), FrpCalibrationModel(platform="Aqua")]
    u_cfg = get_uncertainty_config()
    for plat in ("Terra", "Aqua"):
        pair = p[(p[plat] > 0) & (p["NOAA-20"] > 0)].copy()
        n = len(pair)
        days = int(pd.to_datetime(pair["date"]).nunique()) if n else 0
        if n < MIN_PAIRED_CELLDAYS or days < MIN_PAIRED_DAYS:
            out.append(FrpCalibrationModel(platform=plat, n_paired_cell_days=n, n_paired_days=days))
            continue
        pair = pair.rename(columns={plat: "plat_frp", "NOAA-20": "ref_frp"})
        ratio = float(pair["ref_frp"].sum() / pair["plat_frp"].sum())
        boot = compute_block_bootstrap_ratios(
            pair, num_col="ref_frp", denom_col="plat_frp", date_col="date",
            block_days=u_cfg["block_days"], reps=u_cfg["reps"],
            interval_level=u_cfg["interval_level"], random_seed=random_seed,
        )
        t_tr, t_te, s_tr, s_te = _split_masks(pair)

        def _h(tr_m, te_m, basis):
            tr, te = pair[tr_m], pair[te_m]
            if te.empty or len(tr) < MIN_PAIRED_CELLDAYS or tr["plat_frp"].sum() <= 0:
                return None
            r = float(tr["ref_frp"].sum() / tr["plat_frp"].sum())
            m = evaluate_monthly_metrics(te["ref_frp"], pd.Series(te["plat_frp"].to_numpy() * r), te["date"], basis=basis)
            m.n_train_cell_days = len(tr)
            return m

        temporal, spatial = _h(t_tr, t_te, "temporal_holdout"), _h(s_tr, s_te, "spatial_holdout")
        out.append(FrpCalibrationModel(
            platform=plat, status="ok" if (temporal or spatial) else "unvalidated",
            frp_ratio=round(ratio, 4), uncertainty=boot, metrics_temporal=temporal, metrics_spatial=spatial,
            n_paired_cell_days=n, n_paired_days=days,
        ))
    return out


# -----------------------------------------------------------------------------
# Suite
# -----------------------------------------------------------------------------


def _grain_score(terra: PlatformCalibrationModel, aqua: PlatformCalibrationModel) -> float | None:
    s = [m.selection_score for m in (terra, aqua) if m.selection_score is not None]
    return float(np.mean(s)) if s else None


def fit_calibration_suite(
    obs_clean: pd.DataFrame, method_id: str | None = None, random_seed: int = 42
) -> CalibrationSuite:
    """Fit on SP observations. Method and grain are chosen by held-out error; in-sample error is not used to select."""
    cfg = get_harmonization_config()
    fallback = method_id or cfg.get("enabled_methods", ["stratified_ratio"])[0]
    platform_rule = cfg.get("modis_platform_rule", "aqua_preferred")

    clean = prepare_calibration_data(obs_clean)
    matrix_df = create_cell_day_matrix(clean)

    aqua_rows = matrix_df[matrix_df["aqua_count"] > 0] if not matrix_df.empty else matrix_df
    aqua_min = str(aqua_rows["date"].min()) if len(aqua_rows) else None
    aqua_max = str(aqua_rows["date"].max()) if len(aqua_rows) else None
    bridge_info = bridge_snpp_and_noaa20(matrix_df)

    train_day = build_training_universe(matrix_df, grain="cell_day")
    train_week = build_training_universe(matrix_df, grain="cell_week")

    terra_d = select_platform_model(train_day, "Terra", fallback, random_seed)
    aqua_d = select_platform_model(train_day, "Aqua", fallback, random_seed)
    terra_w = select_platform_model(train_week, "Terra", fallback, random_seed)
    aqua_w = select_platform_model(train_week, "Aqua", fallback, random_seed)
    day_score, week_score = _grain_score(terra_d, aqua_d), _grain_score(terra_w, aqua_w)

    if week_score is not None and (day_score is None or week_score < day_score):
        grain, terra_model, aqua_model, joint_model = "cell_week", terra_w, aqua_w, fit_joint_model(train_week, random_seed)
    else:
        grain, terra_model, aqua_model, joint_model = "cell_day", terra_d, aqua_d, fit_joint_model(train_day, random_seed)

    default_method = next((m.method_id for m in (aqua_model, terra_model) if m.status != "insufficient"), fallback)
    total_cell_days = int(((matrix_df["modis_count"] > 0) | (matrix_df["viirs_count"] > 0)).sum()) if not matrix_df.empty else 0

    try:
        frp_models = fit_frp_calibration(clean, random_seed)
    except Exception:
        logger.exception("FRP calibration failed")
        frp_models = []

    return CalibrationSuite(
        default_method_id=default_method, terra_model=terra_model, aqua_model=aqua_model, joint_model=joint_model,
        bridge_info=bridge_info, total_cell_days_fit=total_cell_days, modis_platform_rule=platform_rule,
        aqua_min_date=aqua_min, aqua_max_date=aqua_max, training_grain=grain,
        mae_monthly_day=round(day_score, 4) if day_score is not None else None,
        mae_monthly_week=round(week_score, 4) if week_score is not None else None,
        frp_models=frp_models,
    )


# -----------------------------------------------------------------------------
# Apply and persist
# -----------------------------------------------------------------------------


def _estimate(mod: PlatformCalibrationModel, counts: np.ndarray, matrix: pd.DataFrame) -> np.ndarray:
    """MODIS-to-VIIRS estimate. NaN (not zero) when the model is insufficient."""
    if mod.status == "insufficient" or (mod.method_id != "identity" and mod.global_ratio is None):
        return np.full(len(counts), np.nan)
    g = mod.global_ratio
    if mod.method_id == "identity":
        return counts
    if mod.method_id == "stratified_ratio":
        keys = matrix["month"].astype(str) + "_" + matrix["day_night"].astype(str)
        return counts * keys.map(mod.strata_ratios).fillna(g).to_numpy(dtype=float)
    if mod.method_id == "count_regression" and "const" in mod.regression_params:
        c, b = mod.regression_params["const"], mod.regression_params.get("log_modis", 1.0)
        return np.where(counts > 0, np.exp(c + b * np.log1p(counts)), 0.0)
    return counts * g


def apply_calibration_to_cell_days(
    cell_day_df: pd.DataFrame,
    suite: CalibrationSuite,
    data_dir: Path | None = None,
    data_version: str | None = None,
) -> pd.DataFrame:
    """Build the harmonized_cell_day mart. VIIRS era (>= 2012-01-20): harmonized = VIIRS observation (identity).
    Earlier dates use the MODIS estimate, or null if no valid calibration exists. Day/night kept separate."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    matrix = create_cell_day_matrix(cell_day_df)

    harm_cols = [
        "h3_cell", "acq_date", "day_night", "region_id",
        "harmonized_value", "harmonized_lower", "harmonized_upper",
        "modis_observed", "modis_terra_observed", "modis_aqua_observed",
        "viirs_observed", "viirs_platform", "platform_used",
        "interval_level", "method_id", "value_type",
        "is_provisional", "calibration_version", "data_version",
    ]
    if matrix.empty:
        empty_df = pd.DataFrame(columns=harm_cols)
        write_mart(empty_df, "harmonized_cell_day", data_dir=base_data_dir)
        return empty_df

    terra_mod, aqua_mod = suite.terra_model, suite.aqua_model
    int_level = terra_mod.uncertainty.get("interval_level", aqua_mod.uncertainty.get("interval_level", 0.9))
    data_version_str = data_version or getattr(settings, "data_version", "dev-0")

    viirs_obs = matrix["viirs_count"].astype(float).values
    modis_obs = matrix["modis_count"].astype(float).values
    terra_c = matrix["terra_count"].astype(float).values
    aqua_c = matrix["aqua_count"].astype(float).values

    t_pred = _estimate(terra_mod, terra_c, matrix)
    a_pred = _estimate(aqua_mod, aqua_c, matrix)
    est_val = np.where(aqua_c > 0, a_pred, np.where(terra_c > 0, t_pred, 0.0))
    est_plat = np.where(aqua_c > 0, "Aqua", np.where(terra_c > 0, "Terra", "none"))

    def _rel(mod, key):
        return mod.uncertainty.get(key, np.nan) if mod.status != "insufficient" else np.nan

    est_lower = np.where(aqua_c > 0, np.maximum(0.0, est_val * (1.0 - _rel(aqua_mod, "rel_lower_err"))),
                         np.where(terra_c > 0, np.maximum(0.0, est_val * (1.0 - _rel(terra_mod, "rel_lower_err"))), 0.0))
    est_upper = np.where(aqua_c > 0, est_val * (1.0 + _rel(aqua_mod, "rel_upper_err")),
                         np.where(terra_c > 0, est_val * (1.0 + _rel(terra_mod, "rel_upper_err")), 0.0))

    date_series = pd.to_datetime(matrix["date"])
    has_viirs_ref = (matrix["viirs_platform"].astype(str) != "none").any() or (viirs_obs > 0).any()
    is_viirs_era = (date_series >= pd.to_datetime("2012-01-20")).values if has_viirs_ref else np.zeros(len(matrix), dtype=bool)

    harm_val = np.where(is_viirs_era, viirs_obs, est_val)
    harm_lower = np.where(is_viirs_era, viirs_obs, est_lower)
    harm_upper = np.where(is_viirs_era, viirs_obs, est_upper)
    plat_used = np.where(is_viirs_era, matrix["viirs_platform"], est_plat)
    val_type = np.where(is_viirs_era, "observed", "estimated, extrapolated")
    meth_id = np.where(is_viirs_era, "identity", suite.default_method_id)

    harm_df = pd.DataFrame({
        "h3_cell": matrix["h3_cell"].astype(str),
        "acq_date": matrix["date"],
        "day_night": matrix["day_night"].astype(str),
        "region_id": "all",
        "harmonized_value": np.round(harm_val, 4),
        "harmonized_lower": np.round(harm_lower, 4),
        "harmonized_upper": np.round(harm_upper, 4),
        "modis_observed": np.round(modis_obs, 4),
        "modis_terra_observed": np.round(terra_c, 4),
        "modis_aqua_observed": np.round(aqua_c, 4),
        "viirs_observed": np.round(viirs_obs, 4),
        "viirs_platform": matrix["viirs_platform"].astype(str),
        "platform_used": plat_used.astype(str),
        "interval_level": float(int_level),
        "method_id": meth_id.astype(str),
        "value_type": val_type.astype(str),
        "is_provisional": matrix["is_provisional"].fillna(False).astype(bool),
        "calibration_version": str(suite.calibration_version),
        "data_version": str(data_version_str),
    }, columns=harm_cols)

    write_mart(harm_df, "harmonized_cell_day", data_dir=base_data_dir)
    save_calibration_models_mart(suite, data_dir=base_data_dir)
    save_frp_calibration_mart(suite, data_dir=base_data_dir)
    return harm_df


def _m(metrics: ModelMetrics | None, attr: str):
    return getattr(metrics, attr) if metrics is not None else None


def save_calibration_models_mart(suite: CalibrationSuite, data_dir: Path | None = None) -> Path:
    """Write data/marts/calibration_models.parquet. Metric columns are in-sample unless prefixed temporal_/spatial_."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    recs = []
    for mod in [suite.terra_model, suite.aqua_model, suite.joint_model]:
        if mod is None:
            continue
        recs.append({
            "platform": mod.platform, "target_sensor": mod.target_sensor, "method_id": mod.method_id,
            "status": mod.status, "global_ratio": mod.global_ratio,
            "strata_ratios_json": json.dumps(mod.strata_ratios),
            "regression_params_json": json.dumps(mod.regression_params),
            "uncertainty_json": json.dumps(mod.uncertainty),
            "n_cell_days_used": mod.metrics.n_cell_days_used,
            "n_months_evaluated": mod.metrics.n_months_evaluated,
            "mae_monthly": mod.metrics.mae_monthly, "rmse_monthly": mod.metrics.rmse_monthly,
            "bias_monthly": mod.metrics.bias_monthly, "rel_mae_monthly": mod.metrics.rel_mae_monthly,
            "metrics_basis": mod.metrics.basis,
            "n_paired_cell_days": mod.n_paired_cell_days, "n_paired_days": mod.n_paired_days,
            "temporal_n_test": _m(mod.metrics_temporal, "n_cell_days_used"),
            "temporal_mae_monthly": _m(mod.metrics_temporal, "mae_monthly"),
            "temporal_rel_mae_monthly": _m(mod.metrics_temporal, "rel_mae_monthly"),
            "temporal_bias_monthly": _m(mod.metrics_temporal, "bias_monthly"),
            "spatial_n_test": _m(mod.metrics_spatial, "n_cell_days_used"),
            "spatial_mae_monthly": _m(mod.metrics_spatial, "mae_monthly"),
            "spatial_rel_mae_monthly": _m(mod.metrics_spatial, "rel_mae_monthly"),
            "spatial_bias_monthly": _m(mod.metrics_spatial, "bias_monthly"),
            "bridge_min_date": suite.bridge_info.min_date, "bridge_max_date": suite.bridge_info.max_date,
            "bridge_ratio": suite.bridge_info.bridge_ratio,
            "modis_platform_rule": suite.modis_platform_rule, "training_grain": suite.training_grain,
            "mae_monthly_day": suite.mae_monthly_day, "mae_monthly_week": suite.mae_monthly_week,
            "calibration_version": suite.calibration_version, "fitted_at": suite.fitted_at,
        })
    df = pd.DataFrame(recs)
    num = [c for c in df.columns if c.endswith(("_n_test", "_monthly", "_ratio", "_used", "_evaluated", "_cell_days", "_days"))
           or c in ("global_ratio", "bridge_ratio", "mae_monthly_day", "mae_monthly_week")]
    for c in num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return write_mart(df, "calibration_models", data_dir=base_data_dir)


def save_frp_calibration_mart(suite: CalibrationSuite, data_dir: Path | None = None) -> Path:
    """Write data/marts/frp_calibration_models.parquet (FRP ratios; separate from count calibration)."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    recs = [{
        "platform": f.platform, "reference": f.reference, "status": f.status, "frp_ratio": f.frp_ratio,
        "uncertainty_json": json.dumps(f.uncertainty),
        "n_paired_cell_days": f.n_paired_cell_days, "n_paired_days": f.n_paired_days,
        "temporal_mae_monthly": _m(f.metrics_temporal, "mae_monthly"),
        "temporal_rel_mae_monthly": _m(f.metrics_temporal, "rel_mae_monthly"),
        "temporal_bias_monthly": _m(f.metrics_temporal, "bias_monthly"),
        "spatial_mae_monthly": _m(f.metrics_spatial, "mae_monthly"),
        "spatial_rel_mae_monthly": _m(f.metrics_spatial, "rel_mae_monthly"),
        "spatial_bias_monthly": _m(f.metrics_spatial, "bias_monthly"),
        "calibration_version": suite.calibration_version, "fitted_at": suite.fitted_at,
    } for f in suite.frp_models]
    df = pd.DataFrame(recs)
    for c in df.columns:
        if c not in ("platform", "reference", "status", "uncertainty_json", "calibration_version", "fitted_at"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return write_mart(df, "frp_calibration_models", data_dir=base_data_dir)