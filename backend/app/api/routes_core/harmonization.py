"""Core API routes: /api/v1/harmonization/comparison and /method."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.storage.duckdb_repo import DuckDBRepository
from app.settings import settings
from app.shared.api_envelope import (
    ApiResponse,
    evaluate_series_and_uncertainty,
    make_meta,
    resolve_api_area,
)

logger = logging.getLogger("terraflare.harmonization")
router = APIRouter(prefix="/harmonization", tags=["harmonization"])
repo = DuckDBRepository()

# Region IDs that mean "no spatial filter".
NO_FILTER_REGIONS = {"india", "global", "all"}
# FALLBACK coverage gates, used only when the coverage_day view is empty (fixture/test mode).
# A day whose total detections are below these is treated as having no coverage.
MIN_DAILY_VIIRS = 1000
MIN_DAILY_MODIS = 1000
# Scientific validity gates for diagnostics (below these -> null + warning).
MIN_CORR_PAIRS = 14       # paired covered days with both sensors observed
MIN_CODET_CELLDAYS = 30   # cell-days with >=1 detection from either sensor
MIN_CODET_DAYS = 7        # distinct paired covered days

COVERAGE_NOTE = (
    "Coverage is taken from ingested file date ranges (a local solar day is covered only if its UTC span "
    "lies inside a sensor's file range), never from detection counts. Days inside a range with zero "
    "detections are flagged suspect and treated as missing, not zero."
)


class ComparisonSeriesItem(BaseModel):
    period: str
    modis_observed: float | None
    viirs_observed: float | None
    harmonized_value: float | None
    lower: float | None
    upper: float | None
    is_provisional: bool | None = None


class OverlapPeriod(BaseModel):
    start: str | None
    end: str | None


class ComparisonDiagnostics(BaseModel):
    correlation: float | None
    co_detection_rate: float | None
    overlap_period: OverlapPeriod
    correlation_n: int | None = None
    co_detection_n: int | None = None
    correlation_deseasonalized: float | None = None


class ComparisonProvenance(BaseModel):
    data_source: str
    data_mode: str
    is_synthetic: bool
    observation_count: int
    date_range: OverlapPeriod
    covered_days: int
    synthetic_rows_detected: int | None = None
    viirs_platforms: list[str] = []
    reliability_status: str
    processing_mode: str | None = None
    coverage_basis: str | None = None
    viirs_covered_days: int | None = None
    modis_covered_days: int | None = None
    value_types: list[str] = []


class ComparisonData(BaseModel):
    region_id: str | None = None
    granularity: str
    series: list[ComparisonSeriesItem]
    diagnostics: ComparisonDiagnostics
    provenance: ComparisonProvenance | None = None


class ComparisonEnvelope(ApiResponse[ComparisonData]):
    pass


class ValidationMetricItem(BaseModel):
    metric: str
    value: float | None
    baseline: str = "identity"


class MethodData(BaseModel):
    method_id: str
    name: str
    description: str
    overlap_period: OverlapPeriod
    assumptions: list[str]
    limitations: list[str]
    validation: list[ValidationMetricItem]


class MethodEnvelope(ApiResponse[MethodData]):
    pass


_COMPARISON_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _clean_str(val: Any, default: str | None = None) -> str | None:
    if val is None or not isinstance(val, str):
        return default
    val = val.strip()
    return val if val else default


def _num(x: Any) -> float | None:
    if x is None or pd.isna(x):
        return None
    return float(x)


def _coverage_table_available() -> bool:
    try:
        return int(repo.con.execute("SELECT COUNT(*) FROM coverage_day").fetchone()[0] or 0) > 0
    except Exception:
        return False


def _cov_cte(use_table: bool) -> str:
    """CTE `cov` with one row per day: covered (VIIRS) and mcovered (MODIS)."""
    if use_table:
        return (
            "WITH cov AS (SELECT CAST(acq_date AS DATE) AS acq_date, "
            "COALESCE(viirs_covered, FALSE) AS covered, COALESCE(modis_covered, FALSE) AS mcovered "
            "FROM coverage_day) "
        )
    return (
        "WITH cov AS (SELECT acq_date, "
        f"SUM(viirs_observed) >= {int(MIN_DAILY_VIIRS)} AS covered, "
        f"SUM(modis_observed) >= {int(MIN_DAILY_MODIS)} AS mcovered "
        "FROM harmonized_cell_day GROUP BY acq_date) "
    )


def _deseasonalized_corr(daily: pd.DataFrame) -> float | None:
    """Pearson r of log1p daily counts after removing a centred 15-day running median (slow seasonal cycle).

    Returns None when fewer than MIN_CORR_PAIRS residual pairs remain or a series has zero variance.
    """
    try:
        d = daily.assign(acq_date=pd.to_datetime(daily["acq_date"])).set_index("acq_date").sort_index()
        res = {}
        for c in ("m", "v"):
            s = np.log1p(d[c].astype(float))
            res[c] = s - s.rolling("15D", center=True, min_periods=8).median()
        r = pd.DataFrame(res).dropna()
        if len(r) < MIN_CORR_PAIRS or r["m"].std() == 0 or r["v"].std() == 0:
            return None
        v = float(np.corrcoef(r["m"], r["v"])[0, 1])
        return None if np.isnan(v) else round(v, 4)
    except Exception:
        logger.exception("deseasonalized correlation failed")
        return None


@router.get("/comparison", response_model=ComparisonEnvelope)
def get_comparison(
    region_id: str | None = Query("global", description="Region ID"),
    bbox: str | None = Query(None, description="Bounding box min_lon,min_lat,max_lon,max_lat"),
    polygon: str | None = Query(None, description="GeoJSON polygon"),
    granularity: str = Query("week", pattern="^(day|week|month)$"),
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
) -> dict[str, Any]:
    region_id = _clean_str(region_id, "global") or "global"
    granularity = _clean_str(granularity, "week") or "week"
    bbox = _clean_str(bbox, None)
    start = _clean_str(start, None)
    end = _clean_str(end, None)

    cache_key = (settings.data_mode, region_id, bbox, str(polygon) if polygon else None, granularity, start, end)
    if cache_key in _COMPARISON_CACHE:
        return _COMPARISON_CACHE[cache_key]

    # ---- Resolve the area. Unknown regions -> 404 (not 500). ----
    needs_area = bool(bbox or polygon) or region_id.lower() not in NO_FILTER_REGIONS
    cells = None
    is_drawn_area = False
    if needs_area:
        try:
            _area_type, cells, is_drawn_area, _bbox_tuple = resolve_api_area(
                region_id=region_id, bbox=bbox, polygon=polygon
            )
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e) or f"Invalid area for region '{region_id}'"
            logger.warning("resolve_api_area failed: %s", msg)
            if "not found" in msg.lower():
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=422, detail=msg)

    params: list[Any] = []
    clauses: list[str] = []

    # LEFT JOIN: mart days absent from the coverage table stay visible and count as not covered.
    cov_join = "LEFT JOIN cov ON h.acq_date = cov.acq_date"

    if cells is not None:
        if len(cells) == 0:
            c_data = ComparisonData(
                region_id=region_id if not is_drawn_area else None,
                granularity=granularity,
                series=[],
                diagnostics=ComparisonDiagnostics(
                    correlation=None,
                    co_detection_rate=None,
                    overlap_period=OverlapPeriod(start=None, end=None),
                ),
            )
            meta = make_meta(reliability="insufficient", warnings=["Area contains no valid grid cells."])
            return {"data": c_data, "meta": meta}
        from_clause = (
            f"FROM harmonized_cell_day h {cov_join} JOIN "
            "(SELECT unnest(?::VARCHAR[]) AS h3_cell) c ON h.h3_cell = c.h3_cell"
        )
        params.append(cells)
    elif region_id.lower() not in NO_FILTER_REGIONS:
        from_clause = f"FROM harmonized_cell_day h {cov_join}"
        clauses.append("h.region_id = ?")
        params.append(region_id)
    else:
        from_clause = f"FROM harmonized_cell_day h {cov_join}"

    if start:
        clauses.append("h.acq_date >= CAST(? AS DATE)")
        params.append(start)
    if end:
        clauses.append("h.acq_date <= CAST(? AS DATE)")
        params.append(end)

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    if granularity == "day":
        period_expr = "strftime(h.acq_date, '%Y-%m-%d')"
    elif granularity == "month":
        period_expr = "strftime(h.acq_date, '%Y-%m')"
    else:
        period_expr = "strftime(h.acq_date, '%G-W%V')"

    use_table = _coverage_table_available()
    cov_cte = _cov_cte(use_table)

    # Values are only summed over days with real coverage, at every granularity.
    query = f"""
        {cov_cte}
        SELECT
            {period_expr} AS period_label,
            ROUND(SUM(CASE WHEN cov.mcovered THEN h.modis_observed END), 2) AS modis_obs,
            ROUND(SUM(CASE WHEN cov.covered THEN h.viirs_observed END), 2) AS viirs_obs,
            ROUND(SUM(CASE WHEN cov.covered THEN h.harmonized_value END), 2) AS harm_val,
            ROUND(SUM(CASE WHEN cov.covered THEN h.harmonized_lower END), 2) AS lower_val,
            ROUND(SUM(CASE WHEN cov.covered THEN h.harmonized_upper END), 2) AS upper_val,
            BOOL_OR(h.is_provisional) AS is_provisional
        {from_clause}
        {where_sql}
        GROUP BY period_label
        ORDER BY period_label ASC
    """

    series_items: list[ComparisonSeriesItem] = []
    total_harm_val = 0.0
    is_any_prov = False
    zero_width_seen = False

    try:
        df = repo.con.execute(query, params).df()
    except Exception as e:
        logger.exception("comparison query failed")
        raise HTTPException(status_code=503, detail=f"harmonization data unavailable: {e}")

    for _, r in df.iterrows():
        m = _num(r["modis_obs"])   # None = not observed, never coerced to 0
        v = _num(r["viirs_obs"])
        h = _num(r["harm_val"])
        lo = _num(r["lower_val"])
        up = _num(r["upper_val"])
        pv = r.get("is_provisional")
        prov = None if pv is None or pd.isna(pv) else bool(pv)
        if prov:
            is_any_prov = True

        # Zero-width interval = no real uncertainty was propagated; do not show it.
        if h is not None and lo is not None and up is not None and lo == up == h:
            lo = up = None
            zero_width_seen = True

        total_harm_val += h or 0.0

        series_items.append(
            ComparisonSeriesItem(
                period=str(r["period_label"]),
                modis_observed=m,
                viirs_observed=v,
                harmonized_value=h,
                lower=lo,
                upper=up,
                is_provisional=prov,
            )
        )

    eff_series, reliability, rel_l, rel_u, warnings = evaluate_series_and_uncertainty(
        expected_count=total_harm_val,
        is_drawn_area=is_drawn_area,
        requested_series="harmonized",
    )
    warnings = list(warnings or [])
        # interval_for() describes MODIS->VIIRS conversion uncertainty; it does not apply to directly observed values.
    _vt = []
    try:
        _vt = [str(r[0]) for r in repo.con.execute(
            "SELECT DISTINCT value_type FROM harmonized_cell_day WHERE value_type IS NOT NULL").fetchall()]
    except Exception:
        pass
    if _vt and set(_vt) == {"observed"}:
        reliability = "insufficient" if (total_harm_val < 10 or not series_items) else (
            "provisional" if is_any_prov else "direct_observation")
        warnings.append(
            "Reliability reflects direct observation (NOAA-20 reference): no conversion uncertainty applies"
            + ("; period includes provisional NRT data." if is_any_prov else "."))
    if use_table:
        warnings.append(COVERAGE_NOTE)
        warnings.append("MODIS and VIIRS values are blank for days without coverage; missing, not zero.")
    else:
        warnings.append(
            f"MODIS values are blank for days with fewer than {MIN_DAILY_MODIS} MODIS detections "
            "(feed not available that day); missing, not zero."
        )
        warnings.append(
            f"Harmonized values are blank for days with fewer than {MIN_DAILY_VIIRS} VIIRS "
            "detections (no or partial VIIRS coverage); these are missing, not zero."
        )
        warnings.append(
            "Coverage fallback: detection-count gates are used because no coverage table is available; "
            "low-activity days can be misread as no coverage."
        )
    if zero_width_seen:
        warnings.append(
            "No calibration interval is available for periods where VIIRS was observed directly."
        )

    # Diagnostics use only days where BOTH sensors have real coverage.
    paired = "cov.covered AND cov.mcovered"
    cov_where = (where_sql + f" AND {paired}") if where_sql else f"WHERE {paired}"
    corr = co_rate = corr_ds = None
    corr_n = codet_n = None
    prov_rows, covered_days, d_min, d_max = 0, 0, None, None
    proc_mode = None
    try:
        daily = repo.con.execute(
            cov_cte + f"SELECT h.acq_date, SUM(h.modis_observed) AS m, SUM(h.viirs_observed) AS v "
            f"{from_clause} {cov_where} GROUP BY h.acq_date ORDER BY h.acq_date", params
        ).df().dropna(subset=["m", "v"])
        covered_days = int(len(daily))
        corr_n = covered_days
        if covered_days < MIN_CORR_PAIRS:
            warnings.append(
                f"Correlation not computed: {covered_days} paired MODIS+VIIRS-covered days "
                f"(< {MIN_CORR_PAIRS} required)."
            )
        elif daily["m"].std() == 0 or daily["v"].std() == 0:
            warnings.append("Correlation not computed: a sensor series has zero variance.")
        else:
            r_val = float(np.corrcoef(daily["m"], daily["v"])[0, 1])
            corr = None if np.isnan(r_val) else round(r_val, 4)
            corr_ds = _deseasonalized_corr(daily)
            warnings.append(
                "Raw correlation includes the shared seasonal cycle and can overstate agreement; the "
                "deseasonalized value is Pearson r of log counts minus a centred 15-day running median."
            )
            if corr_ds is None:
                warnings.append("Deseasonalized correlation not computed: too few paired days after detrending.")
        cd = repo.con.execute(
            cov_cte + "SELECT COUNT(*) FILTER (WHERE h.modis_observed > 0 OR h.viirs_observed > 0), "
            "COUNT(*) FILTER (WHERE h.modis_observed > 0 AND h.viirs_observed > 0) "
            f"{from_clause} {cov_where}", params
        ).fetchone()
        either, both = int(cd[0] or 0), int(cd[1] or 0)
        codet_n = either
        if either < MIN_CODET_CELLDAYS or covered_days < MIN_CODET_DAYS:
            warnings.append(
                f"Co-detection not computed: {either} detected cell-days over {covered_days} "
                f"paired days (need >= {MIN_CODET_CELLDAYS} and >= {MIN_CODET_DAYS})."
            )
        else:
            co_rate = round(both / either, 4)
            warnings.append(
                "Co-detection = cell-days detected by both MODIS and VIIRS / cell-days detected "
                "by either, on days with both MODIS and VIIRS coverage (cell-level, not period-level)."
            )
        pr = repo.con.execute(
            cov_cte + "SELECT COUNT(*), MIN(h.acq_date), MAX(h.acq_date), "
            f"BOOL_OR(h.is_provisional), BOOL_AND(h.is_provisional) {from_clause} {where_sql}", params
        ).fetchone()
        prov_rows = int(pr[0] or 0)
        d_min = str(pr[1]) if pr[1] else None
        d_max = str(pr[2]) if pr[2] else None
        if prov_rows and pr[3] is not None and pr[4] is not None:
            proc_mode = "NRT" if pr[4] else ("MIXED" if pr[3] else "SP")
    except Exception as e:
        logger.exception("diagnostics failed")
        warnings.append(f"Diagnostics unavailable: {e}")

    v_days = m_days = None
    if use_table:
        try:
            cw: list[str] = []
            cp: list[Any] = []
            if start:
                cw.append("acq_date >= CAST(? AS DATE)")
                cp.append(start)
            if end:
                cw.append("acq_date <= CAST(? AS DATE)")
                cp.append(end)
            row = repo.con.execute(
                "SELECT SUM(CASE WHEN viirs_covered THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN modis_covered THEN 1 ELSE 0 END) FROM coverage_day"
                + (" WHERE " + " AND ".join(cw) if cw else ""), cp
            ).fetchone()
            v_days, m_days = int(row[0] or 0), int(row[1] or 0)
        except Exception:
            logger.exception("coverage day counts failed")

    synth_rows = None
    try:
        tot, syn = repo.con.execute(
            "SELECT COUNT(*), COUNT(*) FILTER (WHERE is_synthetic) FROM obs_clean").fetchone()
        if int(tot or 0) == 0:
            warnings.append("is_synthetic could not be verified: obs_clean has no rows in the data lake.")
        else:
            synth_rows = int(syn or 0)
    except Exception:
        warnings.append("Could not verify is_synthetic flag on source observations.")
    is_synth = settings.data_mode == "fixture" or bool(synth_rows)
    if is_synth:
        warnings.insert(0, "SYNTHETIC DATA: values are NOT NASA observations.")
        reliability = "insufficient"
    if prov_rows == 0:
        warnings.append("No harmonized observations for this selection; nothing substituted.")
    viirs_plats: list[str] = []
    try:
        viirs_plats = [
            r[0]
            for r in repo.con.execute(
                "SELECT DISTINCT viirs_platform FROM harmonized_cell_day "
                "WHERE viirs_platform IS NOT NULL "
                "AND lower(viirs_platform) NOT IN ('none', '', 'nan')"
            ).fetchall()
        ]
    except Exception:
        pass
    value_types: list[str] = []
    try:
        value_types = sorted(
            str(r[0]) for r in repo.con.execute(
                "SELECT DISTINCT value_type FROM harmonized_cell_day WHERE value_type IS NOT NULL"
            ).fetchall()
        )
    except Exception:
        pass
    warnings.append(
        "Dates are local solar dates. VIIRS series uses a single reference platform "
        f"({', '.join(viirs_plats) or 'unknown'}); other VIIRS platforms are not summed."
    )
    provenance = ComparisonProvenance(
        data_source=str(repo.data_dir / "marts" / "harmonized_cell_day.parquet"),
        data_mode=settings.data_mode,
        is_synthetic=is_synth,
        observation_count=prov_rows,
        date_range=OverlapPeriod(start=d_min, end=d_max),
        covered_days=covered_days,
        synthetic_rows_detected=synth_rows,
        viirs_platforms=viirs_plats,
        reliability_status=str(reliability),
        processing_mode=proc_mode,
        coverage_basis="ingest_file_ranges" if use_table else "detection_count_gate_fallback",
        viirs_covered_days=v_days,
        modis_covered_days=m_days,
        value_types=value_types,
    )

    overlap_start = overlap_end = None
    try:
        row = repo.con.execute(
            cov_cte + "SELECT MIN(acq_date), MAX(acq_date) FROM cov WHERE covered AND mcovered"
        ).fetchone()
        if row:
            overlap_start = str(row[0]) if row[0] else None
            overlap_end = str(row[1]) if row[1] else None
    except Exception:
        logger.exception("overlap period query failed")

    c_data = ComparisonData(
        region_id=region_id if not is_drawn_area else None,
        granularity=granularity,
        series=series_items,
        diagnostics=ComparisonDiagnostics(
            correlation=corr,
            co_detection_rate=co_rate,
            overlap_period=OverlapPeriod(start=overlap_start, end=overlap_end),
            correlation_n=corr_n,
            co_detection_n=codet_n,
            correlation_deseasonalized=corr_ds,
        ),
        provenance=provenance,
    )
    meta = make_meta(
        series=eff_series,
        method="stratified_ratio",
        is_provisional=is_any_prov,
        reliability=reliability,
        warnings=warnings,
    )
    result = {"data": c_data, "meta": meta}
    if len(_COMPARISON_CACHE) > 128:
        _COMPARISON_CACHE.clear()
    _COMPARISON_CACHE[cache_key] = result
    return result


@router.get("/method", response_model=MethodEnvelope)
def get_harmonization_method() -> dict[str, Any]:
    cal_info = repo.get_calibration_info()
    models = [m for m in (cal_info.get("models") or []) if isinstance(m, dict)]
    by = {str(m.get("platform")): m for m in models}
    aqua, terra = by.get("Aqua"), by.get("Terra")
    primary = aqua if aqua and aqua.get("status") != "insufficient" else terra
    method_id = (primary or {}).get("method_id") or cal_info.get("method_id", "stratified_ratio")

    def f(x: Any) -> float | None:
        try:
            return None if x is None or pd.isna(x) else float(x)
        except Exception:
            return None

    # Bridge overlap is only shown when an overlap was actually found.
    b = cal_info.get("bridge_info", {}) or {}
    overlap_start = str(b["min_date"]) if b.get("min_date") else None
    overlap_end = str(b["max_date"]) if b.get("max_date") else None

    validation_items: list[ValidationMetricItem] = []
    for plat in ("Terra", "Aqua"):
        m = by.get(plat)
        if not m or m.get("status") == "insufficient":
            validation_items.append(ValidationMetricItem(
                metric=f"{plat}: calibration", value=None, baseline="not_available: insufficient paired cell-days"))
            continue
        for key, label, basis in (
            ("temporal_rel_mae_monthly", "relative monthly MAE, temporal holdout (fit before 2025, test 2025)", "temporal_holdout"),
            ("spatial_rel_mae_monthly", "relative monthly MAE, spatial holdout (held-out H3 res-2 blocks)", "spatial_holdout"),
        ):
            validation_items.append(ValidationMetricItem(
                metric=f"{plat}: {label}", value=f(m.get(key)),
                baseline=basis if f(m.get(key)) is not None else "not_computed"))
        validation_items.append(ValidationMetricItem(
            metric=f"{plat}: monthly bias, in-sample", value=f(m.get("bias_monthly")),
            baseline="in_sample: exactly 0 is an identity of the ratio estimator, not accuracy"))

    m_data = MethodData(
        method_id=str(method_id),
        name="Stratified Ratio Harmonization (Aqua-Preferred)",
        description=(
            "Harmonizes MODIS (Terra & Aqua) and VIIRS (NOAA-20 reference; NOAA-21 and S-NPP not used in this dataset) "
            "active-fire hotspot detections into a VIIRS 375m equivalent series. When both Terra and Aqua exist for a "
            "cell-day, Aqua-based prediction is prioritized due to its near-synchronous 13:30 local overpass with VIIRS. "
            "For dates on or after 2012-01-20 the harmonized series equals the single-reference VIIRS observation "
            "(identity, including valid zeros). The MODIS-to-VIIRS conversion is fitted and validated for diagnostics "
            "only and does not enter the 2021-2026 series. A single VIIRS reference series is maintained, never summing "
            "platforms. Hotspot detections are thermal anomalies, not unique fires."
        ),
        overlap_period=OverlapPeriod(start=overlap_start, end=overlap_end),
        assumptions=[
            "VIIRS I-band 375m detection count is the reference scale.",
            "Aqua overpass (~13:30 local solar) closely tracks VIIRS, minimizing diurnal mismatch.",
            "Scaling ratios vary by calendar month and day/night overpass cycle.",
            "Cross-sensor ratios are assumed stationary over the fitting window.",
            "Dates are local solar dates (UTC + longitude/15 h).",
            "Coverage is defined by ingested file date ranges, not detection counts; a local day is covered only if "
            "its full UTC span lies inside the range. Days in range with zero detections are suspect, not valid zeros.",
            "NRT rows are restricted to H3 cells that contain at least one standard-processing detection, so both "
            "streams describe the same footprint.",
            "The calibration method and grain are chosen by held-out error, not in-sample error.",
            "Calibration is fitted on standard-processing data only; NRT is excluded.",
            "FRP is calibrated separately from counts (own ratios, co-detected cell-days only).",
            "Deseasonalized correlation uses log counts minus a centred 15-day running median.",
            "Season Shift and Fire Memory treat a calendar year as complete only if the record spans 1 January to "
            "31 December and at most 14 days lack coverage. The 14-day threshold is an analyst assumption, not a "
            "NASA value. Incomplete years are excluded, never counted as zero activity.",
        
        ],
        limitations=[
            "Ratios are fitted on India standard-processing data and are India-specific.",
            "Held-out error is much larger for unseen regions than for a later year: ratios are stable over time but do not transfer well between areas. The bootstrap interval describes only the aggregate ratio.",
            "No S-NPP/NOAA-20 overlap exists in the data, so no bridge is estimated.",
            "Does not correct for cloud obscuration or smoke blockage.",
            "Intervals are unreliable or absent for small counts (< 10 detections).",
            "NRT observations are provisional and lack final geolocation refinement; where NRT follows standard processing the seam is flagged by is_provisional.",
            "Dates without coverage are missing, not zero detections.",
            "Two MODIS collection versions (6.03 and 61.03) appear in standard processing; no step in yearly ratios was seen, but this is not a formal test.",
            "FRP ratios drift more over time than count ratios and are less reliable.",
        ],
        validation=validation_items,
    )
    meta = make_meta(series="harmonized", method=str(method_id), reliability="insufficient")
    return {"data": m_data, "meta": meta}
def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Rows as dicts with NaN -> None (not available, never 0)."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _gap_ranges(dates: pd.Series, flag: pd.Series) -> list[dict[str, Any]]:
    """Contiguous runs of days where flag is False (outside the ingested file range)."""
    out: list[dict[str, Any]] = []
    run_start = prev = None
    for d, ok in zip(pd.to_datetime(dates), flag.fillna(False).astype(bool)):
        if not ok:
            run_start = run_start or d
            prev = d
        elif run_start is not None:
            out.append({"start": str(run_start.date()), "end": str(prev.date()), "days": int((prev - run_start).days) + 1})
            run_start = prev = None
    if run_start is not None:
        out.append({"start": str(run_start.date()), "end": str(prev.date()), "days": int((prev - run_start).days) + 1})
    return out


@router.get("/coverage")
def get_coverage() -> dict[str, Any]:
    """Per-year sensor coverage from ingested file ranges (never from detection counts)."""
    try:
        df = repo.con.execute("SELECT * FROM coverage_day ORDER BY acq_date").df()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"coverage table unavailable: {e}")
    if df.empty:
        meta = make_meta(reliability="insufficient", warnings=["coverage_day is empty: coverage not available."])
        return {"data": {"years": [], "gaps": {}, "suspect_zero_days": {}}, "meta": meta}
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    df["year"] = df["acq_date"].dt.year
    years = []
    for y, g in df.groupby("year"):
        years.append({
            "year": int(y), "days_in_table": int(len(g)),
            "viirs_covered": int(g["viirs_covered"].fillna(False).sum()),
            "modis_covered": int(g["modis_covered"].fillna(False).sum()),
            "both_covered": int((g["viirs_covered"].fillna(False) & g["modis_covered"].fillna(False)).sum()),
            "viirs_suspect_zero": int(g["viirs_suspect_zero"].fillna(False).sum()),
            "modis_suspect_zero": int(g["modis_suspect_zero"].fillna(False).sum()),
        })
    data = {
        "years": years,
        "gaps": {
            "viirs": _gap_ranges(df["acq_date"], df["viirs_in_range"]),
            "modis": _gap_ranges(df["acq_date"], df["modis_in_range"]),
        },
        "suspect_zero_days": {
            "viirs": [str(d.date()) for d in df.loc[df["viirs_suspect_zero"].fillna(False), "acq_date"]],
            "modis": [str(d.date()) for d in df.loc[df["modis_suspect_zero"].fillna(False), "acq_date"]],
        },
        "basis": "ingest_file_ranges",
        "assumption": COVERAGE_NOTE,
        "source": str(repo.data_dir / "marts" / "coverage_day.parquet"),
        "date_range": {"start": str(df["acq_date"].min().date()), "end": str(df["acq_date"].max().date())},
    }
    warnings = ["Gaps are days outside every ingested file range: missing data, not zero detections."]
    meta = make_meta(series="coverage", method="ingest_file_ranges", warnings=warnings)
    return {"data": data, "meta": meta}


@router.get("/frp-calibration")
def get_frp_calibration() -> dict[str, Any]:
    """FRP ratios (NOAA-20 FRP per MODIS-platform FRP), separate from count calibration. Diagnostic only."""
    p = repo.data_dir / "marts" / "frp_calibration_models.parquet"
    if not p.exists():
        meta = make_meta(reliability="insufficient", warnings=["FRP calibration is not available (file missing)."])
        return {"data": {"models": [], "source": str(p)}, "meta": meta}
    try:
        df = pd.read_parquet(p)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"FRP calibration unreadable: {e}")
    data = {"models": _records(df), "source": str(p), "reference": "NOAA-20"}
    warnings = [
        "FRP ratios are fitted on co-detected cell-days only (FRP exists only where a detection exists).",
        "FRP ratios drift more over time than count ratios (negative temporal bias) and are not applied to the harmonized series.",
        "These coefficients are independent of the count calibration and are never combined with it.",
    ]
    meta = make_meta(series="frp", method="frp_ratio", warnings=warnings)
    return {"data": data, "meta": meta}