# TerraFlare Calibration Decision Record (Task 7f Freeze)

This document formalizes the final calibration architecture, reference standards, uncertainty quantification rules, and explicit assumptions frozen prior to API implementation.

---

## 1. Frozen Calibration Architecture

### Primary Method: Stratified Ratio on Unified MODIS Feature
- **Chosen Method:** `stratified_ratio` stratified by **month $\times$ day/night**.
- **Input Covariate:** Unified MODIS detection count (`modis_used`):
  $$\text{modis\_used} = \begin{cases} \text{Aqua count} & \text{if Aqua detection present} \\ \text{Terra count} & \text{otherwise} \end{cases}$$
- **Evaluation Performance:** Across 4-year leave-one-year-out (LOYO) cross-validation (2019–2022), the unified feature achieves an average out-of-sample relative MAE of **8.99%** (national monthly relative MAE: 6.8% in 2019, 10.1% in 2020, 9.5% in 2021, 9.6% in 2022).
- **Alternative Methods Status:**
  - `identity`: Retained as pass-through during single-sensor periods where direct VIIRS observation exists.
  - `global_ratio`: Retained as global fallback when stratum counts are insufficient ($< 10$ detections).
  - `count_regression` (Poisson/Negative Binomial GLM): Relegated to a non-default experimental model due to severe zero-inflation attenuation and inferior LOYO performance (14.8%–32.9% relative MAE).
  - `regional_stratified_ratio`: Evaluated across 4 bounding box regions but rejected because it degraded out-of-sample error at H3 Resolution 3 (102.86% vs 101.00%) and Resolution 4 (117.23% vs 114.97%).

---

## 2. VIIRS Reference Series Standard

### Single Continuous Reference Platform Rule
- **Mandate:** The reference series is strictly **one VIIRS satellite at any given time**, **never the sum or opportunistic union of multiple VIIRS platforms**.
- **Priority Order:**
  $$\text{S-NPP (Jan 2012 – Present)} \longrightarrow \text{NOAA-20 (on S-NPP outage or retirement)} \longrightarrow \text{NOAA-21}$$
- **Row-Level Tracking:** Every row in `harmonized_cell_day` explicitly records `viirs_platform` (`"S-NPP"`, `"NOAA-20"`, or `"none"`).
- **Seamless Anomaly Bridging:** During the 15-day S-NPP outage in 2022 (July 27 to August 10), NOAA-20 seamlessly functioned as the reference sensor (+258 detections), producing a true continuous reference series of **423,382 detections** in 2022 (eliminating the 642,407 platform-sum inflation).

---

## 3. S-NPP to NOAA-20 Bridging Standard

- **Empirical Ratio:** Evaluated across 961,228 cell-weeks over 2019–2022, the pooled ratio is:
  $$\frac{\sum \text{NOAA-20}}{\sum \text{S-NPP}} = 1.003749 \quad \left(90\%\text{ CI: } [0.985304, 1.022077]\right)$$
- **Bridging Policy:** Because the 90% confidence interval contains 1.0 (half-width `±1.84%`), **no empirical scaling factor or step correction is applied between S-NPP and NOAA-20**.
- **Bridging Uncertainty Term:** An explicit bridging uncertainty half-width of **$\pm 1.84\%$** is added to all harmonized prediction intervals.

---

## 4. Size-Dependent Uncertainty Standard

Uncertainty intervals for harmonized estimates scale dynamically with expected monthly count $\hat{y}$ to accommodate Poisson dispersion in small regions and high precision in macro-aggregates:

$$\hat{y}_{\text{lower}} = \max\left(0, \hat{y} \times (1 - \text{lower\_rel})\right), \quad \hat{y}_{\text{upper}} = \hat{y} \times (1 + \text{upper\_rel})$$

### Configured Class Bins and Bounds (including $\pm 1.84\%$ bridge term)

| Size Class | Expected Monthly Count ($\hat{y}$) | Rel Lower Bound | Rel Upper Bound | Reliability Rating | Empirical 90% Coverage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `very_small` | $[0, 10)$ | 1.018 | 1.238 | `low` | 19.7% |
| `small` | $[10, 50)$ | 0.735 | 6.262 | `low` | 88.1% |
| `medium` | $[50, 250)$ | 0.616 | 4.420 | `low` | 85.6% |
| `large` | $[250, 1000)$ | 0.531 | 2.746 | `low` | 87.3% |
| `very_large` | $[1000, 5000)$ | 0.459 | 1.186 | `low` | 88.6% |
| `macro` | $[5000, \infty)$ | 0.143 | 0.160 | `high` | 91.7% |

- **Reliability Label Assignment:**
  - `high`: Relative interval half-width $\le 0.20$
  - `medium`: Relative interval half-width $\le 0.45$
  - `low`: Relative interval half-width $> 0.45$
- **Production API Interface:** Implemented and exposed via `app.core.harmonization.interval_for(expected_count) -> tuple[float, float, str]`.
- **Observed Counts Rule:** For direct observations (`value_type == "observed"`), $\text{lower} \equiv \text{upper} \equiv \text{observed\_value}$. Uncertainty intervals strictly quantify calibration model parameter uncertainty, not Poisson measurement noise.

---

## 5. Data Hygiene & Ingestion Standards

1. **Static Mask Pooling:** Built from full archive detections at H3 resolution 8 (~1 km) requiring $\ge 3$ distinct days of static activity (types 2/3) and $\ge 50\%$ static share. Detections pooled across VIIRS achieve 96.77% true positive static capture with $<0.88\%$ vegetation false positive rate.
2. **Provisional Flags:** Automatically tagged as `is_provisional = True` for observations occurring on or after NRT stream activation:
   - MODIS: `2026-09-01`
   - VIIRS (all platforms): `2026-08-01`
   All stream boundaries are written to `manifest.json`.
3. **Monthly Slice Integrity:** Trailing spillover days from UTC-to-local midnight conversion are clipped, guaranteeing exactly 48 months in 4-year slice outputs.
4. **Reproducibility:** All random bootstrap generators are seeded deterministically from configuration (`random_seed: 42`).

---

## 6. Explicit List of What Remains Assumed

While the calibration architecture is fully validated on historical observations, the following operational assumptions remain:

1. **Sensor Degradation Linearity:** Aqua's orbit has remained stable (+4 min overpass shift), while Terra has drifted earlier by 10 minutes. It is assumed that detector radiometric calibration on both sensors continues without sudden non-linear optical degradation until decommissioning.
2. **Detection Ratio Stationarity Across Extreme Land-Cover Shifts:** The ratio between MODIS and VIIRS is assumed stationary within each (month $\times$ day/night) stratum. An unprecedented ecological shift (e.g., massive land clearing or novel fire regimes) could alter the sub-pixel fire size distribution and temporarily bias the empirical ratio.
3. **NOAA-21 Bridge Stationarity:** It is assumed that NOAA-21's VIIRS sensor performance matches NOAA-20 within the existing bridging margin ($\pm 1.84\%$). While preliminary overlap confirms high consistency, long-term multi-year validation remains subject to ongoing NOAA-21 operational data accumulation.
4. **Cloud Obscuration Symmetry:** Cloud cover is assumed to obscure MODIS and VIIRS detections proportionally when overpass times are close (~13:20 vs ~13:30). Rapid diurnal cloud development between overpasses is assumed to average out across monthly aggregations.

