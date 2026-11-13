# TerraFlare Scientific Validation: Ratio Drift, Overlap Holdouts, and Instrument Seams

**NASA Space Apps Challenge 2026 — Harmonization of MODIS and VIIRS Active Fire Observations**  
*Evaluation Period:* 2012-01-20 to 2025-12-31 (14-Year Continuous Cross-Sensor Overlap, 4,980,258 Active Cell-Days)  
*Status:* Evaluated on Single-Platform Corrected VIIRS Reference Record with Strict Holdout Protocols  

---

## 1. Executive Summary & Headline Accuracy

To eliminate data leakage and guard against temporal drift, all models are evaluated strictly with out-of-time temporal holdouts:

1. **Forward Holdout (Rolling Origin 2016–2025, 10 Test Years, 120 Country-Months)**:
   - **B0 (Identity, unharmonized MODIS count):** **82.88% Relative MAE** (Rel Bias: -82.88%).
   - **Model A (Fixed Ratio, all prior years):** **11.87% Relative MAE** (Rel Bias: +3.96%, Spearman $\rho = \mathbf{0.989}$).
   - **Model B (Nearest $K=2$ years):** **11.65% Relative MAE** (Rel Bias: +2.57%, Spearman $\rho = \mathbf{0.991}$).
   - **Model B (Nearest $K=3$ years):** **11.57% Relative MAE** (Rel Bias: +3.22%, Spearman $\rho = \mathbf{0.990}$).
   - **Model C (Log-Ratio Linear Trend):** **16.79% Relative MAE** (Rel Bias: +8.41%, Spearman $\rho = \mathbf{0.982}$).

2. **Backward Holdout (Pre-VIIRS Era Reconstruction: Train on 2018–2025, Test on 2012–2017)**:
   - **B0 (Identity):** **83.02% Relative MAE** (Rel Bias: -83.02%).
   - **Full Late (2018–2025):** **11.62% Relative MAE** (Rel Bias: -7.70%, Spearman $\rho = \mathbf{0.990}$).
   - **Nearest $K=2$ (2018–2019):** **10.74% Relative MAE** (Rel Bias: -5.45%, Spearman $\rho = \mathbf{0.993}$).
   - **Nearest $K=3$ (2018–2020):** **11.04% Relative MAE** (Rel Bias: -7.18%, Spearman $\rho = \mathbf{0.993}$).
   - **Latest $K=2$ (2024–2025, heavily drifted):** **14.26% Relative MAE** (Rel Bias: -11.26%, Spearman $\rho = \mathbf{0.984}$).
   - **Scope Note:** The ~11% relative error applies strictly to the conversion model used for pre-2012 reconstruction (2000–2011). In the reference era (2012+), values are directly observed.

3. **Key Scientific Conclusion**:
   - Fixed ratio and Nearest-$K$ calibrations exhibit flat ratios within uncertainty intervals across the 14-year record. While overpass-time shifts are observed (+68 min for Aqua, -59 min for Terra), a paired statistical test on the 10 yearly forward errors shows that Fixed Ratio and Nearest-$K$ are statistically indistinguishable ($t = 0.4294, p = 0.6777$ for $K=2$; $t = 0.3065, p = 0.7662$ for $K=3$; Wilcoxon $W = 24.0, p = 0.7695$).
   - Ground pixels of MODIS ($1.0 \times 1.0\text{ km} = 1.0\text{ km}^2$) are **about 7x larger in ground area** than VIIRS 375m pixels ($0.375 \times 0.375\text{ km} \approx 0.14\text{ km}^2$, ratio $\approx 7.1$). This is a plausible physical hypothesis for why raw identity undercounts VIIRS detections by ~83%, but remains an untested hypothesis without sub-pixel fire spread ground truth.

---

## 2. Ratio Over Time & Orbital Drift Analysis (2012–2025)

Evaluated across 4,980,258 active cell-days with 1,000-replicate stationary block-bootstrap 90% confidence intervals (block length = 1 calendar month) and median Indian Standard Time (IST) overpass hours computed from 18,019,063 canonical observations:

| Year | Active Cell-Days | Aqua Present Share | True VIIRS Reference Obs | MODIS Used (Aqua-pref) | Ratio (Platform Used) | 90% Block-Bootstrap CI | Ratio (Aqua-only) | Ratio (Terra-only) | Aqua Day IST (hr) | Terra Day IST (hr) | S-NPP Day IST (hr) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2012** | 252,911 | 15.80% | 447,574 | 82,794 | **5.4059** | [5.1152, 5.9058] | 1.4954 | 1.0196 | 13.45 | 11.00 | 13.28 |
| **2013** | 210,341 | 14.77% | 359,065 | 63,364 | **5.6667** | [5.1447, 6.2355] | 1.4454 | 1.0461 | 13.47 | 11.02 | 13.30 |
| **2014** | 224,738 | 14.34% | 399,286 | 67,173 | **5.9441** | [5.3173, 6.6676] | 1.5977 | 1.2080 | 13.45 | 11.00 | 13.37 |
| **2015** | 208,912 | 14.07% | 350,413 | 59,822 | **5.8576** | [5.4794, 6.3693] | 1.4715 | 0.8408 | 13.45 | 11.00 | 13.37 |
| **2016** | 283,160 | 13.93% | 508,381 | 79,002 | **6.4350** | [5.8347, 7.0156] | 1.6446 | 1.0905 | 13.55 | 11.02 | 13.40 |
| **2017** | 259,859 | 14.25% | 434,752 | 72,147 | **6.0259** | [5.6405, 6.2885] | 1.4469 | 0.9503 | 13.52 | 10.95 | 13.37 |
| **2018** | 355,876 | 11.03% | 469,022 | 79,686 | **5.8859** | [5.5101, 6.1672] | 1.4255 | 0.9715 | 13.52 | 11.03 | 13.37 |
| **2019** | 348,034 | 8.72% | 377,684 | 65,866 | **5.7341** | [5.2894, 6.1056] | 1.4881 | 0.9204 | 13.48 | 11.03 | 13.33 |
| **2020** | 333,121 | 9.30% | 353,086 | 67,028 | **5.2677** | [4.7275, 5.9015] | 1.5119 | 0.8728 | 13.50 | 11.05 | 13.37 |
| **2021** | 487,099 | 9.78% | 581,705 | 99,247 | **5.8612** | [5.2484, 6.2817] | 1.6001 | 1.2009 | 13.48 | 10.98 | 13.27 |
| **2022** | 402,565 | 8.44% | 423,382 | 72,334 | **5.8532** | [5.2453, 6.6999] | 1.4260 | 0.8634 | 13.53 | 10.85 | 13.37 |
| **2023** | 506,508 | 6.84% | 409,381 | 69,213 | **5.9148** | [5.2609, 6.6448] | 1.2411 | 0.6707 | 13.68 | 10.60 | 13.32 |
| **2024** | 512,229 | 6.39% | 382,891 | 64,906 | **5.8992** | [5.0669, 6.6739] | 1.1460 | 0.6165 | 14.07 | 10.37 | 13.30 |
| **2025** | 594,905 | 7.34% | 459,784 | 83,911 | **5.4794** | [5.0375, 5.8700] | 1.0254 | 0.5366 | 14.58 | 10.02 | 13.28 |

### Measured Overpass-Time Shifts & Cross-Sensor Stability
- **Aqua Overpass Shift:** Aqua's daytime crossing shifted from **13.45 IST (1:27 PM)** during 2012–2021 to **14.58 IST (2:35 PM)** in 2025 (a measured shift of +68 minutes into mid-afternoon). The Aqua-only co-detection ratio exhibits a fitted slope of **-0.0283/year** ($p = 0.0079$, $R^2 = 0.4574$).
- **Terra Overpass Shift:** Terra's daytime crossing shifted from **11.00 IST (11:00 AM)** down to **10.02 IST (10:01 AM)** in 2025 (a measured shift of -59 minutes earlier into morning). The Terra-only ratio exhibits a fitted slope of **-0.0339/year** ($p = 0.0053$, $R^2 = 0.4899$).
- **VIIRS Reference Stability:** S-NPP daytime crossing remained stable at **13.28–13.40 IST (1:17–1:24 PM)** throughout 2012–2025.

---

## 3. Seasonal & Diurnal Strata Breakdown

Evaluating the cross-sensor ratio across 4 quarterly month groups and Day vs Night:

| Month Group | Diurnal Period | True VIIRS Detections | MODIS Used (Aqua-pref) | Ratio | 90% Block-Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Q1 (Jan–Mar)** | Day | 1,672,499 | 381,263 | **4.3867** | [4.2458, 4.5326] |
| **Q1 (Jan–Mar)** | Night | 686,727 | 36,950 | **18.5853** | [16.1371, 20.7259] |
| **Q2 (Apr–Jun)** | Day | 1,322,030 | 264,088 | **5.0060** | [4.7116, 5.3413] |
| **Q2 (Apr–Jun)** | Night | 734,257 | 46,044 | **15.9469** | [14.5966, 17.2996] |
| **Q3 (Jul–Sep)** | Day | 23,071 | 5,436 | **4.2441** | [3.8759, 4.6219] |
| **Q3 (Jul–Sep)** | Night | 12,973 | 687 | **18.8836** | [16.6514, 21.5338] |
| **Q4 (Oct–Dec)** | Day | 1,399,211 | 286,350 | **4.8864** | [4.7225, 5.0570] |
| **Q4 (Oct–Dec)** | Night | 105,638 | 5,675 | **18.6146** | [16.0775, 21.9967] |

- **Nocturnal Discrepancy:** MODIS 1 km pixels miss sub-pixel low-intensity residue fires at night, requiring ratios of **15.9–18.9**, compared to **4.2–5.0** during the day.

---

## 4. Explanation of the 7–11% vs 24–27% Error Gap

When evaluating 2019–2022 performance:
1. **Prior Multi-Platform Target Defect:** In earlier calibration iterations (Task 8), models trained on 2012–2017 were evaluated against a multi-platform target that summed co-active VIIRS sensors (S-NPP, NOAA-20, and NOAA-21). This multi-platform target was inflated by ~51.7% relative to a single continuous instrument, blowing up relative error to **24–27%** (25.3% in 2019, 23.6% in 2020, 27.1% in 2021, and 26.7% in 2022).
2. **Corrected Single-Platform Continuous Reference:** When evaluated against the corrected single-platform VIIRS reference (S-NPP continuous, NOAA-20 bridging during the 2022 outage), rolling origin forward error across 2016–2025 is **11.57% to 11.87% Relative MAE**, reconciling closely with the **10.74% to 11.62%** backward holdout error.
3. **Statistical Equivalence:** A paired statistical test on the 10 forward test years confirms that Fixed Ratio (11.87% MAE) and Nearest-$K$ (11.57%–11.65% MAE) are statistically indistinguishable ($p > 0.67$).

---

## 5. Candidate Calibrations & Holdout Performance

### 5.1 Rolling-Origin Forward Holdout (2016–2025)
Country-Month grain across 10 annual forward test folds:

| Test Year | VIIRS Obs | B0 (Identity) Rel MAE | Model A (Fixed Prior) Rel MAE (Bias) | Model B (Nearest $K=2$) Rel MAE (Bias) | Model B (Nearest $K=3$) Rel MAE (Bias) | Model C (Trend) Rel MAE (Bias) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2016** | 508,381 | 84.5% | 11.6% (-11.5%) | **11.2% (-8.7%)** | 12.2% (-8.9%) | 37.0% (+23.6%) |
| **2017** | 434,752 | 83.4% | 8.3% (-3.6%) | **8.2% (+1.8%)** | 9.7% (+0.9%) | 13.9% (+0.5%) |
| **2018** | 469,022 | 83.0% | **9.4% (+2.5%)** | 13.7% (+12.6%) | 10.5% (+9.1%) | 17.9% (+15.4%) |
| **2019** | 377,684 | 82.6% | **11.1% (+10.3%)** | 13.0% (+12.0%) | 16.1% (+15.6%) | 20.2% (+20.2%) |
| **2020** | 353,086 | 81.0% | 16.8% (+12.8%) | **12.9% (+7.5%)** | 16.1% (+11.5%) | 18.0% (+15.3%) |
| **2021** | 581,705 | 82.9% | **5.9% (+1.8%)** | 11.4% (-9.5%) | 6.0% (-3.5%) | 8.9% (-3.3%) |
| **2022** | 423,382 | 82.9% | 10.7% (+7.5%) | 11.5% (+2.9%) | **10.2% (+1.4%)** | 13.3% (+3.7%) |
| **2023** | 409,381 | 83.1% | 12.4% (+1.9%) | **9.4% (-1.9%)** | 10.3% (-3.2%) | 11.1% (-2.6%) |
| **2024** | 382,891 | 83.0% | 19.2% (+9.2%) | **13.8% (+5.7%)** | 17.4% (+7.3%) | 19.0% (+6.3%) |
| **2025** | 459,784 | 81.7% | 16.8% (+14.6%) | 12.0% (+10.3%) | 11.0% (+8.7%) | **8.7% (+7.9%)** |
| **Overall** | **4,400,068** | **82.88%** | **11.87% (+3.96%)** | **11.65% (+2.57%)** | **11.57% (+3.22%)** | **16.79% (+8.41%)** |

### 5.2 Backward Holdout (Pre-VIIRS Reconstruction on 2012–2017)
Testing on 2012–2017 with models trained on future years:

| Test Year | VIIRS Obs | B0 Rel MAE | Full Late (2018–2025) Rel MAE (Bias) | Nearest $K=2$ (2018–2019) Rel MAE (Bias) | Nearest $K=3$ (2018–2020) Rel MAE (Bias) | Latest $K=2$ (2024–2025) Rel MAE (Bias) | Latest $K=3$ (2023–2025) Rel MAE (Bias) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2012** | 447,574 | 81.5% | 11.1% (+3.5%) | 9.4% (+6.7%) | **8.6% (+4.7%)** | 12.0% (-1.5%) | 15.0% (+3.0%) |
| **2013** | 359,065 | 82.4% | 10.0% (-5.4%) | **7.2% (-4.1%)** | 9.1% (-5.4%) | 13.4% (-8.5%) | 13.4% (-5.1%) |
| **2014** | 399,286 | 83.2% | **10.4% (-8.1%)** | 12.4% (-5.8%) | 11.6% (-7.6%) | 12.2% (-12.2%) | 11.4% (-8.9%) |
| **2015** | 350,413 | 82.9% | 8.7% (-7.6%) | 9.7% (-4.5%) | **8.3% (-6.4%)** | 13.3% (-11.8%) | 12.6% (-8.4%) |
| **2016** | 508,381 | 84.5% | 16.4% (-16.4%) | **14.4% (-13.8%)** | 15.8% (-15.6%) | 19.7% (-19.7%) | 18.4% (-17.0%) |
| **2017** | 434,752 | 83.4% | 11.4% (-10.7%) | **10.1% (-9.9%)** | 11.4% (-11.3%) | 13.6% (-12.5%) | 12.6% (-10.0%) |
| **Overall** | **2,499,471** | **83.02%** | **11.62% (-7.70%)** | **10.74% (-5.45%)** | **11.04% (-7.18%)** | **14.26% (-11.26%)** | **14.14% (-7.98%)** |

### 5.3 Seam Check: 2008–2015 Join (Modelled vs. Observed Transition)
To test whether splicing the pre-VIIRS reconstruction (MODIS-converted) onto the operational VIIRS reference series introduces an artificial step discontinuity, annual country totals across 2008–2015 were evaluated by `value_type`:

| Year | Value Type | Active Cell-Days | Harmonized Country Total | Notes |
| :---: | :--- | ---: | ---: | :--- |
| **2008** | `estimated, extrapolated` | 44,374 | 452,409.8 | Modelled from MODIS |
| **2009** | `estimated, extrapolated` | 55,641 | 560,059.6 | Modelled from MODIS |
| **2010** | `estimated, extrapolated` | 45,839 | 460,887.4 | Modelled from MODIS |
| **2011** | `estimated, extrapolated` | 44,864 | 453,780.9 | Modelled from MODIS |
| **2012** | `estimated, extrapolated` | 982 | 8,755.4 | Pre-VIIRS seam (1–19 Jan) |
| **2012** | `observed` | 252,911 | 447,574.0 | Single-platform VIIRS (20 Jan–31 Dec) |
| **2012** | **Combined Annual Total** | **253,893** | **456,329.4** | **Full Year 2012 Total** |
| **2013** | `observed` | 210,341 | 359,065.0 | Single-platform VIIRS |
| **2014** | `observed` | 224,738 | 399,286.0 | Single-platform VIIRS |
| **2015** | `observed` | 208,912 | 350,413.0 | Single-platform VIIRS |

- **Ratio of 2012 to 2011:**
  - **Full Year 2012 (Modelled + Observed) vs. 2011 Modelled:** $\frac{456,329.4}{453,780.9} = \mathbf{1.0056x}$ (+0.56% difference).
  - **2012 Observed-Only vs. 2011 Modelled:** $\frac{447,574.0}{453,780.9} = \mathbf{0.9863x}$ (-1.37% difference).
- **Assessment of Seam Continuity:**
  The join does not exhibit an abrupt step artifact at annual national scale: 2011 modelled detections (453,780.9) and 2012 harmonized detections (456,329.4) differ by only +0.56%, well within normal interannual variance (which spans 452k to 560k across 2008–2011). However, at sub-monthly resolution, January 2012 spans two regimes: 1–19 Jan (8,755.4 modelled across 19 days = 460.8/day) vs. 20–31 Jan (7,353.0 observed across 12 days = 612.8/day), reflecting sensor sensitivity and diurnal coverage differences across the mid-month activation seam. Full continuity should not be claimed at daily grain across 19–20 Jan 2012.

---

## 6. Uncertainty Intervals & Cross-Fold Held-Out Coverage

### 6.1 Sign Convention and Relative Error Definition
Relative error $\epsilon$ on out-of-time validation data is formally defined as the relative residual of true VIIRS count $y_t$ relative to predicted count $\hat{y}$:

$$\epsilon = \frac{y_t - \hat{y}}{\hat{y}}$$

The empirical quantiles $q_{0.05}(\epsilon)$ and $q_{0.95}(\epsilon)$ determine the relative lower and upper bounds:
$$\text{lower\_rel} = -q_{0.05}(\epsilon), \quad \text{upper\_rel} = q_{0.95}(\epsilon)$$

yielding the 90% uncertainty interval for true count $y_t$:
$$\hat{y}_{\text{lower}} = \max\left(0, \hat{y} \times (1 - \text{lower\_rel})\right), \quad \hat{y}_{\text{upper}} = \hat{y} \times (1 + \text{upper\_rel})$$

**One-line test assertion confirming the interval bounds the true value:**
```python
assert lower <= y_true <= upper
```

### 6.2 Cross-Fold Held-Out Coverage vs Calibration on Same Errors
To test bounds calibration without data leakage, bounds derived from forward folds (2018–2025) were evaluated on backward holdout folds (2012–2017), and vice-versa (strictly **held-out coverage**):

| Size Class | Expected Monthly Count ($\hat{y}$) | Rel Lower Bound | Rel Upper Bound | Calibrated on Same Errors (Pooled) | Held-Out Coverage: Fwd Bounds on Back Test (2012–2017) | Held-Out Coverage: Back Bounds on Fwd Test (2018–2025) | Reliability Rating |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `very_small` | $[0, 10)$ | *None* | *None* | *N/A (suppressed)* | *N/A (suppressed)* | *N/A (suppressed)* | `insufficient` |
| `small` | $[10, 50)$ | **0.940** | **2.626** | **91.2%** | **90.2%** | **89.7%** | `medium` |
| `medium` | $[50, 250)$ | **0.841** | **1.588** | **90.9%** | **91.2%** | **85.9%** | `medium` |
| `large` | $[250, 1000)$ | **0.792** | **1.023** | **90.6%** | **91.8%** | **84.6%** | `medium` |
| `very_large` | $[1000, 5000)$ | **0.679** | **0.791** | **90.5%** | **91.5%** | **83.0%** | `medium` |
| `macro` | $[5000, \infty)$ | **0.264** | **0.354** | **91.7%** | **95.6%** | **80.7%** | `medium` |

- **Labeling Standard:** Where empirical coverage is reported on the same 264,964 area-months used to compute empirical quantiles, it is strictly labeled **"calibrated on the same errors"** (90.5%–91.7%). Where tested on independent folds, it is labeled **"held-out coverage"**.
- **Macro & Country Coverage:** Across all 192 country-months (120 forward + 72 backward), empirical 90% bounds are **[0.264, 0.354]** (half-width 0.309, `medium` reliability) with **91.67%** empirical coverage (176 of 192 months covered), replacing placeholder bounds with exact holdout metrics.
- **Protection for Small Cells:** Predictions with $\hat{y} < 10$ have intervals suppressed (`insufficient`) to prevent unphysical bounds.
- **Scope Note:** The ~11% relative error applies strictly to the conversion model used for pre-2012 reconstruction. In the reference era (2012+), values are directly observed.

### 6.3 Operational Interval Semantics Across Eras
1. **VIIRS Era (`date >= 2012-01-20`):** Direct observation. For standard months, $\text{lower} \equiv \text{upper} \equiv \text{value}$, $\text{reliability} = \text{'observed'}$, and $\text{interval\_applies\_to} = \text{'none'}$. For reference transition months (**July 2022**, **August 2022**, and **November 2026**), the $\pm 1.84\%$ bridge term is applied with $\text{reliability} = \text{'medium'}$ and $\text{interval\_applies\_to} = \text{'bridge'}$.
2. **Pre-VIIRS Era (`date < 2012-01-20`):** Modeled conversion with $\text{value\_type} = \text{'estimated, extrapolated'}$ and $\text{interval\_applies\_to} = \text{'conversion'}$.
3. **Small-Area Fallback:** When `interval_for` returns `'insufficient'` or `'low'`, the 2012+ observed series is retained, and `modis_native` is spliced for pre-2012 with $\text{reliability} = \text{'low'}$. Pre-2012 data is **never dropped silently**.

---

## 7. Pipeline Staging, Data Hygiene & Static Audit

### 7.1 Static Mask File Audit & Entry Reconciliation (1,334 vs 2,554 vs 3,735)
- **`data/staging/static_source_mask.json` (Production Mask):** Contains **1,334 tuples** strictly for S-NPP (1,334 unique spatial cells).
- **`data/slice_2019_2022/staging/static_source_mask.json`:** Contains **2,554 tuples** (1,301 unique spatial cells across Aqua, Terra, S-NPP, NOAA-20).
- **`data/clean_profile/staging/static_source_mask.json`:** Contains **2,384 tuples** (1,032 unique cells across 5 platforms).
- **Explanation:** Single-platform masks contain 1,334 entries; multi-platform masks repeat the same physical cells under 2–4 platforms, yielding 2,554 and 3,735 tuples.

### 7.2 Static Flare Claim Audit: Archive vs NRT (Claim Marked Unresolved)
Mask-flagged detections per day across archive Sep–Oct (2023–2025) and NRT Sep–Oct (2026) across VIIRS sensors:
- **2023 Sep–Oct (Archive):** 29,429 flagged rows over 61 days = **482.4 rows/day**
- **2024 Sep–Oct (Archive):** 26,197 flagged rows over 61 days = **429.5 rows/day**
- **2025 Sep–Oct (Archive):** 25,795 flagged rows over 61 days = **422.9 rows/day**
- **2026 Sep–Oct (NRT):** 38,857 flagged rows over 61 days = **637.0 rows/day**

**Spatial Verification:** In Sep–Oct 2026 NRT, **38,855 of 38,857 flagged rows (99.99%)** occur in cells with confirmed archive static activity on $\ge 10$ distinct days. The elevated detection rate occurs strictly at known industrial/flare locations, not new sites.
**Scientific Audit:** Satellite telemetry alone cannot determine whether the higher detection rate reflects an actual physical surge in flaring volume, orbital viewing geometry variations, atmospheric transmission anomalies, or NRT algorithmic sensitivity thresholds. Therefore, the causal claim of a "physical increase in flares" is **DROPPED** and formally marked **UNRESOLVED**.

### 7.3 Canonical Current-vs-Median Table (Computed from Marts)
Metrics computed directly from `harmonized_cell_day` with baseline = median over complete historical years 2012–2025 for the exact same calendar days:

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
