# TerraFlare Calibration Decision Record

This document formalizes the final calibration architecture, reference standards, uncertainty quantification rules, and explicit assumptions frozen following out-of-time forward and backward validation and double-count elimination.

---

## 1. Frozen Calibration Architecture

### Primary Method: Dynamic Nearest-$K$ Stratified Ratio on Unified MODIS Feature
- **Chosen Method:** `stratified_ratio` stratified by **month $\times$ day/night**, calibrated dynamically over overlap years, accounting for measured overpass-time shifts (+68 min Aqua, -59 min Terra).
- **Input Covariate:** Unified MODIS detection count (`modis_used`):
  $$\text{modis\_used} = \begin{cases} \text{Aqua count} & \text{if Aqua detection present} \\ \text{Terra count} & \text{otherwise} \end{cases}$$
- **Out-of-Time Forward Validation Headline (Rolling Origin 2016–2025, 120 Country-Months):**
  - **B0 (Identity, uncalibrated MODIS):** **82.88% Relative MAE** (Rel Bias: -82.88%). The ~7:1 to 9:1 pixel-area ratio ($1.00\text{ km}^2$ vs $0.14\text{ km}^2$) is a plausible physical hypothesis for the uncalibrated ~83% undercount, but remains an untested explanation without sub-pixel fire spread ground truth.
  - **Model A (Fixed Ratio, all historical years):** **11.87% Relative MAE** (Rel Bias: +3.96%, Spearman $\rho = 0.989$).
  - **Model B (Nearest $K=2$ years):** **11.65% Relative MAE** (Rel Bias: +2.57%, Spearman $\rho = 0.991$).
  - **Model B (Nearest $K=3$ years):** **11.57% Relative MAE** (Rel Bias: +3.22%, Spearman $\rho = 0.990$).
  - **Model C (Log-Ratio Linear Trend):** **16.79% Relative MAE** (Rel Bias: +8.41%, Spearman $\rho = 0.982$).
- **Backward Holdout Validation (Reconstructing Pre-VIIRS 2000–2011: Train on 2018–2025, Test on 2012–2017):**
  - **B0 (Identity):** **83.02% Relative MAE** (Rel Bias: -83.02%).
  - **Full Late (2018–2025):** **11.62% Relative MAE** (Rel Bias: -7.70%, Spearman $\rho = 0.990$).
  - **Nearest $K=2$ (2018–2019):** **10.74% Relative MAE** (Rel Bias: -5.45%, Spearman $\rho = 0.993$).
  - **Nearest $K=3$ (2018–2020):** **11.04% Relative MAE** (Rel Bias: -7.18%, Spearman $\rho = 0.993$).
  - **Latest $K=2$ (2024–2025, heavily drifted):** **14.26% Relative MAE** (Rel Bias: -11.26%, Spearman $\rho = 0.984$).
  - **Scope Note:** The ~11% relative error applies strictly to the conversion model used for pre-2012 reconstruction (2000–2011). In the reference era (2012+), values are directly observed.
- **Resolution of Historical LOYO Diagnostic vs Out-of-Time Holdout:**
  - The previously reported 24–27% error gap when testing 2012–2017 training on 2019–2022 was an artifact of the earlier multi-platform target formulation, which summed multiple VIIRS satellites (S-NPP, NOAA-20, NOAA-21) and artificially inflated the reference sum by ~51.7%.
  - When evaluated against the corrected single-platform VIIRS reference series, forward rolling-origin error across 2016–2025 is **11.57% to 11.87% Relative MAE**, reconciling closely with the **10.74% to 11.62%** backward holdout error.
  - A paired statistical test on the 10 yearly forward errors confirms that Fixed Ratio (11.87% MAE) and Nearest-$K$ (11.57%–11.65% MAE) are statistically indistinguishable ($t = 0.4294, p = 0.6777$ for $K=2$; $t = 0.3065, p = 0.7662$ for $K=3$; Wilcoxon $W = 24.0, p = 0.7695$).
- **Alternative Methods Status:**
  - `identity`: Retained strictly during single-sensor periods where direct VIIRS observation exists.
  - `global_ratio`: Retained as global fallback when stratum counts are insufficient ($< 10$ detections).
  - `count_regression` (Poisson/Negative Binomial GLM): Relegated to a non-default experimental model due to severe zero-inflation attenuation and inferior performance (14.2%–32.2% relative MAE).
  - `regional_stratified_ratio`: Evaluated across 4 bounding box regions but rejected because it degraded out-of-sample error at H3 Resolution 3 (122.01% vs 121.82%) and Resolution 4 (139.87% vs 139.08%).

---

## 2. VIIRS Reference Series Standard & Elimination of Double Count

### Single Continuous Reference Platform Rule
- **Mandate:** The reference series is strictly **one VIIRS satellite at any given time**, **never the sum or opportunistic union of multiple VIIRS platforms**.
- **Priority Order:**
  $$\text{S-NPP (Jan 2012 – 2 Nov 2026 data end date)} \longrightarrow \text{NOAA-20 (from 2 Nov 2026)} \longrightarrow \text{NOAA-21}$$
- **Data-Driven Transition:** S-NPP serves as reference until its empirical data end date read dynamically from the data (**2 November 2026**).
  - S-NPP's final day (2 Nov 2026) has detections only within a 6-minute window (13:58 to 14:04 UTC) representing a single orbital pass, and is treated as **incomplete**.
  - NOAA-20 provides complete 24-hour continuous coverage starting on 2 Nov 2026, ensuring no data gap.
- **Post-S-NPP Verification:** Detections for 3–9 Nov 2026 strictly utilize NOAA-20 as the reference sensor (verified by fixture test `test_viirs_reference_order_november_2026`).
- **Row-Level Tracking:** Every row in `harmonized_cell_day` explicitly records `viirs_platform` (`"S-NPP"`, `"NOAA-20"`, or `"none"`).

### Elimination of VIIRS-Era Double Count & Product Policy
- **Architectural Defect Identified:** In earlier versions, cell-days with active MODIS fires where VIIRS detected 0 fires had `viirs_platform == 'none'`. The harmonization step assigned an estimated value to these rows instead of 0.0, injecting **4,094,331.3 spurious detections** across 2012–2026 into the reference era.
- **Permanent Correction:**
  - For the **VIIRS Era (`date >= 2012-01-20`)**: The harmonized value **strictly equals the single-platform VIIRS reference series, including zeros** (`harm_val = viirs_obs`, `value_type = "observed"`). In cells where VIIRS observed no fire, `harm_val` is strictly 0.0.
  - For the **Pre-VIIRS Era (`date < 2012-01-20`)**: Direct VIIRS observation is unavailable. The harmonized value is estimated via the calibrated stratified ratio, with uncertainty intervals computed from backward holdout errors, labeled with `value_type = "estimated, extrapolated"` in database rows and API responses.
- **Seamless Anomaly Bridging (423,382 2022 Total):**
  - In calendar year 2022, S-NPP recorded **423,124 detections**.
  - During the 15-day S-NPP anomaly outage (27 July to 10 August 2022), NOAA-20 seamlessly provided **+258 detections** of bridging reference coverage.
  - The true annual 2022 continuous reference total is **423,382 detections** ($423,124 + 258$).

---

## 3. S-NPP to NOAA-20 Bridging Standard

- **Empirical Ratio:** Evaluated across 961,228 cell-weeks over 2019–2022, the pooled ratio is:
  $$\frac{\sum \text{NOAA-20}}{\sum \text{S-NPP}} = 1.003749 \quad \left(90\%\text{ CI: } [0.985304, 1.022077]\right)$$
- **Bridging Policy:** Because the 90% confidence interval contains 1.0 (half-width `±1.84%`), **no empirical scaling factor or step correction is applied between S-NPP and NOAA-20**.
- **Bridging Uncertainty Term:** An explicit bridging uncertainty half-width of **$\pm 1.84\%$** is added to harmonized intervals strictly for months where the reference platform transitioned (July 2022, August 2022, November 2026). Standard observed months have $\text{lower} \equiv \text{upper} \equiv \text{value}$ with $\text{reliability} = \text{'observed'}$ and $\text{interval\_applies\_to} = \text{'none'}$.

---

## 4. Size-Dependent Uncertainty Standard (Out-of-Time Holdout Calibration)

### 4.1 Sign Convention and Relative Error Definition
Relative error $\epsilon$ on out-of-time validation data is formally defined as the relative residual of true VIIRS count $y_t$ relative to predicted count $\hat{y}$:

$$\epsilon = \frac{y_t - \hat{y}}{\hat{y}}$$

The empirical quantiles $q_{0.05}(\epsilon)$ and $q_{0.95}(\epsilon)$ determine the relative lower and upper multipliers:
$$\text{lower\_rel} = -q_{0.05}(\epsilon), \quad \text{upper\_rel} = q_{0.95}(\epsilon)$$

yielding the 90% uncertainty interval for true count $y_t$:
$$\hat{y}_{\text{lower}} = \max\left(0, \hat{y} \times (1 - \text{lower\_rel})\right), \quad \hat{y}_{\text{upper}} = \hat{y} \times (1 + \text{upper\_rel})$$

**One-line test assertion confirming the interval bounds the true value:**
```python
assert lower <= y_true <= upper
```

### 4.2 Cross-Fold Held-Out Uncertainty Coverage
To verify bounds calibration without data leakage, bounds derived from forward folds (2018–2025) are tested on backward holdout folds (2012–2017), and vice-versa (strictly **held-out coverage**):

| Size Class | Expected Monthly Count ($\hat{y}$) | Rel Lower Bound | Rel Upper Bound | Calibrated on Same Errors (Pooled) | Held-Out Coverage: Fwd Bounds on Back Test (2012–2017) | Held-Out Coverage: Back Bounds on Fwd Test (2018–2025) | Reliability Rating |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `very_small` | $[0, 10)$ | *None* | *None* | *N/A (suppressed)* | *N/A (suppressed)* | *N/A (suppressed)* | `insufficient` |
| `small` | $[10, 50)$ | **0.940** | **2.626** | **91.2%** | **90.2%** | **89.7%** | `medium` |
| `medium` | $[50, 250)$ | **0.841** | **1.588** | **90.9%** | **91.2%** | **85.9%** | `medium` |
| `large` | $[250, 1000)$ | **0.792** | **1.023** | **90.6%** | **91.8%** | **84.6%** | `medium` |
| `very_large` | $[1000, 5000)$ | **0.679** | **0.791** | **90.5%** | **91.5%** | **83.0%** | `medium` |
| `macro` | $[5000, \infty)$ | **0.264** | **0.354** | **91.7%** | **95.6%** | **80.7%** | `medium` |

- **Labeling Standard:**
  - Where quantiles are evaluated on the identical 264,964 area-months used to fit the empirical quantiles, coverage is strictly labeled **"calibrated on the same errors"** (90.5%–91.7%).
  - Where quantiles are tested on independent out-of-time folds, coverage is labeled **"held-out coverage"**.
- **Macro & Country Coverage:** At country scale (India nationwide, 192 holdout months), coverage under macro bounds is **91.67%** (176 of 192 country-months covered with bounds [0.264, 0.354], half-width 0.309, assigning `medium` reliability under the half-width $\le 0.45$ threshold).
- **Pre-2012 Conversion Error:** The ~11% relative error applies strictly to the MODIS-to-VIIRS conversion model applied to the pre-2012 reconstruction era (2000–2011).

### 4.3 Operational Interval Semantics Across Eras
1. **VIIRS Era (`date >= 2012-01-20`):**
   - Harmonized value is directly observed from the single-platform VIIRS reference.
   - For standard months: $\text{lower} \equiv \text{upper} \equiv \text{value}$, $\text{reliability} = \text{'observed'}$, and $\text{interval\_applies\_to} = \text{'none'}$.
   - For reference platform transition months (**July 2022**, **August 2022**, and **November 2026**), the empirical bridging uncertainty ($\pm 1.84\%$) is applied:
     $$\text{lower} = \max(0, \text{round}(\text{value} \times (1 - 0.0184), 1)), \quad \text{upper} = \text{round}(\text{value} \times (1 + 0.0184), 1)$$
     with $\text{reliability} = \text{'medium'}$ and $\text{interval\_applies\_to} = \text{'bridge'}$.
2. **Pre-VIIRS Era (`date < 2012-01-20`):**
   - Values are modeled from MODIS observations with `value_type = 'estimated, extrapolated'`.
   - Bounds come from the backward-holdout conversion error distribution (`interval_applies_to = 'conversion'`).
3. **Small-Area Fallback Behavior:**
   - When an area is too small for reliable harmonization (`interval_for` returns `'insufficient'` or `'low'`), the system retains the 2012+ directly observed VIIRS series and splices `modis_native` counts (with $\text{reliability} = \text{'low'}$ and a warning) for the pre-2012 portion. Pre-2012 historical data is **never dropped silently**.
4. **API Response Metadata Fields:**
   - `value_type`: `'observed'` for 2012+ direct observations; `'estimated, extrapolated'` for pre-2012 modeled values.
   - `interval_applies_to`: `'none'` for standard observed months; `'bridge'` for transition months ($\pm 1.84\%$); `'conversion'` for pre-2012 modeled values.

---

## 5. Data Hygiene, Static Masking & Ingestion Standards

### 5.1 Static Mask File Audit & Entry Reconciliation (1,334 vs 2,554 vs 3,735)
The static mask stores persistent high-temperature industrial emitters (flares, refineries, steel plants) identified from the archive:
- **`data/staging/static_source_mask.json` (Production Mask):** Contains **1,334 tuples** strictly for S-NPP (1,334 unique spatial H3 cells).
- **`data/slice_2019_2022/staging/static_source_mask.json`:** Contains **2,554 tuples** (1,301 unique cells across Aqua, Terra, S-NPP, and NOAA-20).
- **`data/clean_profile/staging/static_source_mask.json`:** Contains **2,384 tuples** (1,032 unique cells across 5 platforms).
- **Explanation of Discrepancy (1,334 vs 2,554 and 3,735):** The mask JSON structure is a list of `[platform, h3_cell]` pairs. In the production mart, static exclusion is enforced per-platform (1,334 cells for S-NPP). Earlier reports citing 2,554 and 3,735 entries evaluated multi-platform pooled masks where the same ~1,000–1,300 physical spatial cells were duplicated across 2–4 platforms (Aqua, Terra, S-NPP, NOAA-20, NOAA-21).

#### Reconciliation of NRT Static Detections (48,631 vs 14,423):
- **48,631 Rows (Task 7f Scope):** Represents all NRT detections flagged as `possible_static_source` across **ALL 5 platforms** (MODIS Terra/Aqua, and VIIRS S-NPP/NOAA-20/NOAA-21) in raw/staging ingestion (48,059 valid nominal/high confidence + 572 sub-nominal confidence dropped during cleaning).
- **14,423 Rows (Task 7g Scope):** Represents static detections excluded specifically from the primary VIIRS reference series (**S-NPP alone**) during monthly reference aggregation. Both S-NPP and NOAA-20 static rows are excluded from aggregation via `static_masked=True` and `possible_static_source`.

| Year-Month | Platform | Stream | Total NRT Detections | Flagged Static Detections | Static Share (%) | Scope |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **2026-08** | NOAA-20 | NRT | 2,455 | 1,248 | 50.84% | All Platforms (7f) |
| **2026-08** | NOAA-21 | NRT | 2,270 | 1,224 | 53.92% | All Platforms (7f) |
| **2026-08** | **S-NPP** | NRT | 2,247 | **1,259** | 56.03% | **Reference Excluded (7g)** |
| **2026-09** | Aqua | NRT | 301 | 159 | 52.82% | All Platforms (7f) |
| **2026-09** | NOAA-20 | NRT | 6,821 | 4,299 | 63.03% | All Platforms (7f) |
| **2026-09** | NOAA-21 | NRT | 6,764 | 4,364 | 64.52% | All Platforms (7f) |
| **2026-09** | **S-NPP** | NRT | 6,625 | **4,347** | 65.62% | **Reference Excluded (7g)** |
| **2026-09** | Terra | NRT | 387 | 225 | 58.14% | All Platforms (7f) |
| **2026-10** | Aqua | NRT | 2,041 | 317 | 15.53% | All Platforms (7f) |
| **2026-10** | NOAA-20 | NRT | 24,900 | 8,953 | 35.96% | All Platforms (7f) |
| **2026-10** | NOAA-21 | NRT | 21,464 | 8,343 | 38.87% | All Platforms (7f) |
| **2026-10** | **S-NPP** | NRT | 21,201 | **8,551** | 40.33% | **Reference Excluded (7g)** |
| **2026-10** | Terra | NRT | 1,174 | 465 | 39.61% | All Platforms (7f) |
| **2026-11** | Aqua | NRT | 4,161 | 74 | 1.78% | All Platforms (7f) |
| **2026-11** | NOAA-20 | NRT | 12,244 | 2,028 | 16.56% | All Platforms (7f) |
| **2026-11** | NOAA-21 | NRT | 12,355 | 1,826 | 14.78% | All Platforms (7f) |
| **2026-11** | **S-NPP** | NRT | 1,506 | **266** | 17.66% | **Reference Excluded (7g)** |
| **2026-11** | Terra | NRT | 647 | 111 | 17.16% | All Platforms (7f) |
| **TOTALS** | **All 5 Platforms** | NRT | **128,991** | **48,059** (+572 dropped = **48,631**) | **37.53%** | **Task 7f Screening** |
| **TOTALS** | **S-NPP Reference** | NRT | **31,579** | **14,423** | **45.67%** | **Task 7g S-NPP Exclusion** |

### 5.2 Archive Vegetation History Screening & Contamination Warning
Across 79,691 historical vegetation fire cells (archive `fire_type == '0'`), NRT detections occurring in cells with no prior archive vegetation history were screened:
- **2026-08 (31 days):** 12 / 6,972 (0.119% $\le 0.20\%$) $\implies$ clean.
- **2026-09 (30 days):** 17 / 20,898 (0.081% $\le 0.20\%$) $\implies$ clean.
- **2026-10 (31 days):** 148 / 70,780 (**0.209% > 0.20%**) $\implies$ triggers `possible_static_contamination` warning.
- **2026-11 (Days 1–9):** 61 / 30,913 (0.197% $\le 0.20\%$) $\implies$ clean.
- **Contamination Warning Rule:** When the share of NRT detections in cells with no archive vegetation history exceeds `static_contamination_threshold_pct: 0.20` (0.20%), the API appends a `possible_static_contamination` warning (triggered for October 2026 at 0.209%).

### 5.3 Static Flare Claim Audit: Archive vs NRT (Claim Marked Unresolved)
To audit the earlier hypothesis of a "physical increase in flares", mask-flagged detections per day were evaluated across archive Sep–Oct (2023–2025) and NRT Sep–Oct (2026) across all 3 VIIRS sensors (NOAA-20, NOAA-21, S-NPP):
- **2023 Sep–Oct (Archive):** 29,429 flagged rows over 61 days = **482.4 rows/day**
- **2024 Sep–Oct (Archive):** 26,197 flagged rows over 61 days = **429.5 rows/day**
- **2025 Sep–Oct (Archive):** 25,795 flagged rows over 61 days = **422.9 rows/day**
- **2026 Sep–Oct (NRT):** 38,857 flagged rows over 61 days = **637.0 rows/day**

**Spatial Verification:** In Sep–Oct 2026 NRT, **38,855 of 38,857 flagged rows (99.99%)** occur in cells with confirmed archive static activity on $\ge 10$ distinct days. The elevated detection rate occurs strictly at known industrial/flare locations, not new sites.
**Scientific Audit:** Satellite telemetry alone cannot determine whether the higher detection rate reflects an actual physical surge in flaring volume, orbital viewing geometry variations, atmospheric transmission anomalies, or NRT algorithmic sensitivity thresholds. Therefore, the causal claim of a "physical increase in flares" is **DROPPED** and formally marked **UNRESOLVED**.

### 5.4 Canonical Current-vs-Median Table (Computed from Marts)
All metrics are computed directly from the canonical marts (`harmonized_cell_day`) using baseline = median over complete historical years 2012–2025 for the exact same calendar days:

| Month | Days Evaluated | Stage 2 Detections (Marts) | Baseline Median (2012–2025) | Baseline IQR [Q25, Q75] | Current vs Baseline Ratio | Baseline Percentile |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **August 2026** | Full Month (Days 1–31) | **965** | 494.5 | [414.2, 604.8] | **1.951x** | 92.9% |
| **September 2026** | Full Month (Days 1–30) | **2,061** | 1,198.0 | [1008.2, 1360.2] | **1.720x** | 100.0% |
| **October 2026** | Full Month (Days 1–31) | **10,645** | 28,651.0 | [21806.2, 34720.8] | **0.372x** | 14.3% |
| **November 2026** | Partial Month (Days 1–9) | **9,029** | 27,639.5 | [22134.2, 38018.2] | **0.327x** | 7.1% |

- **Resolution of Experimental Tighter Mask (794 vs. 200 Cells):**
  During sensitivity analysis, a stricter static filtering threshold (`min_distinct_days >= 5`, `min_static_pct >= 80%`) was evaluated against the production standard (`min_distinct_days >= 3`, `min_static_pct >= 50%`). In historical sensitivity trials on multi-platform pooled candidates, this tighter criterion identified 794 cells, while on single-platform S-NPP archive observations it isolated exactly 200 cells. The tighter mask produced nearly identical suppressed current-vs-median ratios (0.343x vs 0.327x in Nov), but failed to mask 1,134 legitimate persistent industrial sources active on 3–4 days or at 50–79% static frequency. Consequently, the production mask (1,334 cells) is retained as the sole operational standard, and experimental tighter mask columns have been removed.

#### Pipeline Staging Breakdown for August–November 2026:
- **Stage 1 (Raw VIIRS Reference before cleaning & static mask):**
  - August 2026: **2,247** (S-NPP raw)
  - September 2026: **6,625** (S-NPP raw)
  - October 2026: **21,201** (S-NPP raw)
  - November 2026 (Nov 1–9): **12,604** (1,506 S-NPP on Nov 1–2 + 11,098 NOAA-20 on Nov 3–9)
- **Stage 2 (Published Marts `harmonized_cell_day` after cleaning & static exclusion):**
  - August 2026: **965**
  - September 2026: **2,061**
  - October 2026: **10,645**
  - November 2026 (Nov 1–9): **9,029** (1,104 S-NPP + 7,925 NOAA-20)

---

## 6. Explicit List of What Remains Assumed

While the calibration architecture is fully validated on historical observations, the following operational assumptions remain:

1. **Overpass-Time Shifts:** Aqua's daytime crossing shifted by **+68 minutes** (from 13:28 to 14:35 IST in 2025) and Terra shifted by **-59 minutes** (from 11:00 to 10:01 IST in 2025). The calibration tracks measured shifts across the historical record, assuming that instrument detection response remains stable across operational years.
2. **Detection Ratio Stationarity Across Extreme Land-Cover Shifts:** The ratio between MODIS and VIIRS is assumed stationary within each (month $\times$ day/night) stratum over localized multi-year windows. An unprecedented ecological shift (e.g., massive permanent land clearing or novel fire regimes) could alter the sub-pixel fire size distribution and temporarily bias the empirical ratio.
3. **NOAA-21 Bridge Stationarity:** It is assumed that NOAA-21's VIIRS sensor performance matches NOAA-20 within the existing bridging margin ($\pm 1.84\%$). While preliminary overlap confirms high consistency, long-term multi-year validation remains subject to ongoing NOAA-21 operational data accumulation.
4. **Cloud Obscuration Symmetry:** Cloud cover is assumed to obscure MODIS and VIIRS detections proportionally when overpass times are close (~13:20 vs ~13:30). Rapid diurnal cloud development between overpasses is assumed to average out across monthly aggregations.
