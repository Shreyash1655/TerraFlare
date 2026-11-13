# TerraFlare Open Items & Engineering Audit (Task 11)

This document tracks all completed engineering verifications, resolved action items, and standing operational items for future satellite mission phases.

---

## 1. Codebase Audit: TODO / FIXME / VERIFY Scan

An exhaustive codebase search across `backend/`, `scripts/`, and `config/` for `# TODO`, `# FIXME`, `# HACK`, and `# VERIFY` comments confirmed:
- **Unaddressed TODOs:** 0
- **Unaddressed FIXMEs:** 0
- **Unaddressed HACKs:** 0
- **Verification Comments:** All occurrences of `verify` in the codebase are active test assertion docstrings in `backend/tests/` that pass deterministically in CI.

---

## 2. Completed Major Engineering Verifications (Tasks 1–11)

| Task / Item | Description | Status | Verification Reference |
| :--- | :--- | :---: | :--- |
| **Task 7f: Single Reference Rule** | Never sum VIIRS platforms. Exactly one reference platform per observation period (S-NPP -> NOAA-20 -> NOAA-21). | **VERIFIED** | `test_viirs_reference_order_november_2026` |
| **Task 7g: Static NRT Exclusion** | Static source NRT rows flagged and excluded identically across all platforms via `static_masked=True` and `qc_flags`. | **VERIFIED** | `test_noaa20_static_nrt_rows_excluded_november_2026` |
| **Task 8b: Double Count Elimination** | In the VIIRS era (`date >= 2012-01-20`), harmonized value strictly equals single-platform VIIRS reference (including zeros). MODIS-converted values are never added on top. | **VERIFIED** | `test_viirs_era_double_count_elimination` |
| **Task 8b: Ratio Drift Tracking** | Measured overpass-time drift (+68 min for Aqua, -59 min for Terra) tracked via dynamic Nearest-$K$ calibration ($K=2$ or $3$). | **VERIFIED** | `scripts/evaluate_ratio_drift.py`, `docs/VALIDATION.md` |
| **Task 8b: Rebuilt Holdout Intervals** | Uncertainty bounds rebuilt from 264,964 out-of-time forward/backward holdouts, achieving 90.5%–91.7% empirical coverage across active size classes and 91.7% at country scale ([0.264, 0.354] bounds, medium reliability). | **VERIFIED** | `scripts/rebuild_holdout_intervals.py`, `docs/CALIBRATION_DECISION.md` |
| **Task 10: Core API Envelope & Routing** | Standard `{data, meta}` envelope, spatial validators, pattern parameter validation, and streaming CSV export. | **VERIFIED** | `backend/tests/core/test_api_core.py`, `scripts/smoke_test.py` |
| **Task 11: Data Serving Package** | Self-contained serving package script `scripts/package_serving_data.py` and deployment manual `docs/DEPLOY.md`. | **VERIFIED** | `docs/DEPLOY.md` |

---

## 3. Standing Operational & Future Mission Items

The following items are designated for future operational monitoring as NASA and NOAA release updated data products:

1. **NOAA-21 Longitudinal Bridging:**
   - *Context:* NOAA-21 (JPSS-2) VIIRS standard processing archive begins on 2023-03-01, continuing through 2026-07-31 in archive, with near-real-time observations through November 2026.
   - *Operational Item:* Evaluate a formal multi-year cross-sensor bridge ratio once extended operational data accumulates.
2. **Post-Decommissioning MODIS Archive:**
   - *Context:* When Terra and Aqua are officially decommissioned, NASA is expected to release a final consistent historical Collection 6.1 reprocessing (release timeline subject to agency scheduling).
   - *Operational Item:* Refresh `data/staging/obs_clean.parquet` with the final frozen archive release to freeze the pre-VIIRS (2000–2011) reconstruction permanently.
3. **Automated Mart Synchronization:**
   - *Context:* Daily NRT feeds can be appended via scheduled cron/pipeline workflows.
   - *Operational Item:* Maintain pipeline stage isolation (`--stage clean --stage cell_day --stage harmonize`) to append incremental daily observations without refitting historical models.
4. **2000–2002 Terra-Only Historical Era:**
   - *Context:* The backward holdout validation (evaluating 2012–2017 with models trained on 2018–2025) operates on the dual-platform MODIS era (where both Aqua and Terra are active). The earliest historical pre-VIIRS era (November 2000 to June 2002) contains Terra observations alone prior to Aqua's operational commencement (2002-05-04).
   - *Operational Item:* While the platform-used calibration rule cleanly handles Terra-only cell-days via Terra-specific stratum ratios, users should note that this single-sensor era is not covered by the backward holdout test fold.

