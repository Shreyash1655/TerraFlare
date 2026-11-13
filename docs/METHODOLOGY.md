# TerraFlare Scientific Methodology & Algorithmic Design

This document details the exact mathematical and algorithmic methods implemented in the TerraFlare codebase, from raw sensor ingestion to calibrated historical harmonization and serving analytics.

---

## 1. Raw Data Ingestion & Quality Control

### 1.1 Ingestion Pipeline
TerraFlare ingests NASA FIRMS active fire products across 5 satellite platforms:
- **MODIS:** Terra (morning/night) and Aqua (afternoon/night) Collection 6.1 (Standard Processing and NRT).
- **VIIRS 375m:** S-NPP, NOAA-20 (JPSS-1), and NOAA-21 (JPSS-2) Collection 2 (Standard Processing and NRT).

### 1.2 Coordinate Validation & Spatial Indexing
- **Spatial Domain (India National Bounding Box):** Longitude $68.0^\circ \text{E}$ to $97.5^\circ \text{E}$, Latitude $6.5^\circ \text{N}$ to $37.5^\circ \text{N}$. Detections outside these bounds or with invalid coordinates are rejected during ingestion.
- **H3 Discrete Global Grid:** Each detection is mapped to an Uber H3 Resolution 6 hexagon (average area $\approx 36.1\text{ km}^2$, edge length $\approx 3.7\text{ km}$).

### 1.3 Time Normalization
Detections are acquired in UTC. TerraFlare computes:
$$\text{Local Time (IST)} = \text{UTC Time} + 05:30$$
$$\text{Local Date} = \text{Date of Local Time in IST}$$
This ensures diurnal agricultural burning events (typically peaking between 12:00 and 15:30 IST) are grouped into the correct local calendar day rather than split across UTC date boundaries.

### 1.4 Confidence Standardization
- **MODIS:** Scaled from $0–100\%$ into classes: `low` ($< 30\%$), `nominal` ($30\% \le C < 80\%$), and `high` ($\ge 80\%$). Sub-nominal records are flagged during cleaning.
- **VIIRS:** Direct classification into `low`, `nominal`, and `high` based on the native FIRMS 375m algorithm.

### 1.5 Static Source Masking (Industrial & Flare Screening)
Archive records include a `fire_type` tag: `0` (presumed vegetation fire), `2` (other static land source), and `3` (offshore static source).
- Archive static detections (`fire_type` $\in \{2, 3\}$) are excluded from active fire aggregation.
- A persistent static mask is built across high-frequency detection cells ($\ge 3$ distinct operational days with $\ge 50\%$ static history).
- Near-Real-Time (NRT) rows falling into this static mask are tagged `possible_static_source` and `static_masked = True`, and are excluded from harmonized aggregation identically across all platforms (S-NPP, NOAA-20, NOAA-21, Terra, Aqua).

---

## 2. Harmonization & Sensor Calibration

### 2.1 The Single Continuous Reference Platform Rule
VIIRS observations from different satellites are **never summed or combined opportunistically**. At any given time, exactly one satellite provides the continuous reference series:
1. **S-NPP:** Reference standard from **20 January 2012** through its empirical data end date (**2 November 2026**). S-NPP's final day (2 Nov 2026) has detections only within a 6-minute window (13:58 to 14:04 UTC) representing a single orbital pass, and is treated as incomplete.
2. **NOAA-20:** Reference standard starting **2 November 2026** onwards, providing seamless 24-hour continuous coverage without a data gap.
3. **NOAA-21:** Secondary backup.

### 2.2 S-NPP to NOAA-20 Sensor Bridging
Evaluated across 961,228 cell-weeks over 2019–2022:
$$\frac{\sum \text{NOAA-20}}{\sum \text{S-NPP}} = 1.003749 \quad (90\%\text{ CI: } [0.985304, 1.022077])$$
Because the 90% confidence interval covers 1.0 (half-width $\pm 1.84\%$), no step scaling adjustment is applied. Instead, a bridging uncertainty term of $\pm 1.84\%$ is explicitly incorporated into all prediction intervals.

### 2.3 Elimination of VIIRS-Era Double Count & Product Policy
- **VIIRS Era ($\ge \text{2012-01-20}$):** The harmonized count strictly equals the single-platform VIIRS reference series, including true zeros:
  $$\text{harmonized\_value} = \text{viirs\_observed}, \quad \text{value\_type} = \text{"observed"}$$
  Cells where MODIS detected fires but VIIRS detected 0 fires on operational satellite days are assigned $\text{harmonized\_value} = 0.0$. MODIS-converted values are **never added on top of the reference series**.
- **Pre-VIIRS Era ($< \text{2012-01-20}$):** VIIRS observations do not exist. MODIS detections are converted to VIIRS-equivalent units using the nearest overlap calibration:
  $$\text{harmonized\_value} = \text{modis\_used} \times \beta_{m, d}, \quad \text{value\_type} = \text{"estimated, extrapolated"}$$
  where $\text{modis\_used}$ selects Aqua if present, else Terra.

### 2.4 Mathematical Calibration Model: Stratified Ratio
Due to massive zero-inflation in daily 36 km² cells (>90% zero cells) and extreme nocturnal contrast, linear count regression (Poisson/Negative Binomial GLMs) attenuates slopes toward zero. TerraFlare uses a **Stratified Ratio** model stratified by **Month $\times$ Diurnal Period (Day/Night)**:

$$\beta_{m, d} = \frac{\sum_{i \in \text{train}_{m, d}} \text{VIIRS}_i}{\sum_{i \in \text{train}_{m, d}} \text{MODIS\_used}_i}$$

Diurnal ratios reflect the physical sensitivity of the sensors:
- **Daytime Ratios:** $4.2$ to $5.0$, reflecting VIIRS 375m pixels detecting low-intensity residue fires obscured to MODIS 1 km pixels.
- **Nighttime Ratios:** $15.9$ to $18.9$, capturing sub-pixel nocturnal cooling and low background contrasts.

---

## 3. Out-of-Time Holdout Validation & Orbital Drift

### 3.1 Headline Out-of-Time Accuracy
All models are evaluated exclusively with temporal holdouts:
1. **Forward Holdout (Rolling Origin 2016–2025, 120 Country-Months):**
   - **B0 (Identity):** 82.88% Relative MAE (MODIS 1 km pixels are ~7x larger than VIIRS 375m pixels).
   - **Nearest $K=2$ Years:** **11.65% Relative MAE** (Bias: +2.57%, Spearman $\rho = 0.991$).
   - **Nearest $K=3$ Years:** **11.57% Relative MAE** (Bias: +3.22%, Spearman $\rho = 0.990$).
2. **Backward Holdout (Pre-VIIRS Era Reconstruction: Train on 2018–2025, Test on 2012–2017):**
   - **Nearest $K=2$ Years:** **10.74% Relative MAE** (Bias: -5.45%, Spearman $\rho = 0.993$).
   - **Nearest $K=3$ Years:** **11.04% Relative MAE** (Bias: -7.18%, Spearman $\rho = 0.993$).

### 3.2 Measured Overpass-Time Drift
- **Aqua:** Overpass shifted by **+68 minutes** (from 13:28 IST in 2012–2021 to 14:35 IST in 2025). Aqua-only ratio trends downward by $-0.0283/\text{year}$ ($p = 0.0079$).
- **Terra:** Overpass shifted by **-59 minutes** (from 11:00 IST to 10:01 IST in 2025). Terra-only ratio trends downward by $-0.0339/\text{year}$ ($p = 0.0053$).
- **S-NPP:** Overpass remained locked at 13:17–13:24 IST.
Dynamic Nearest-$K$ calibration accounts for this measured drift by fitting on the nearest available overlap years.

---

## 4. Size-Dependent Uncertainty Quantification

Uncertainty bounds scale dynamically with expected monthly count $\hat{y}$ to accommodate Poisson dispersion:

$$\hat{y}_{\text{lower}} = \max\left(0, \hat{y} \times (1 - \text{lower\_rel})\right), \quad \hat{y}_{\text{upper}} = \hat{y} \times (1 + \text{upper\_rel})$$

### 4.1 Rebuilt Holdout Interval Bounds
Evaluated across **264,964 out-of-time area-months** from rolling forward and backward holdouts:

| Size Class | Range ($\hat{y}$) | Share of Area-Months | Rel Lower Bound | Rel Upper Bound | Half-width | Reliability Rating | Empirical 90% Coverage |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `very_small` | $[0, 10)$ | **57.73%** | *None* | *None* | *None* | `insufficient` | *N/A (suppressed)* |
| `small` | $[10, 50)$ | **19.76%** | 0.940 | 2.626 | 1.783 | `low` | **91.2%** |
| `medium` | $[50, 250)$ | **11.42%** | 0.841 | 1.588 | 1.215 | `low` | **90.9%** |
| `large` | $[250, 1000)$ | **3.99%** | 0.792 | 1.023 | 0.907 | `low` | **90.6%** |
| `very_large` | $[1000, 5000)$ | **1.19%** | 0.679 | 0.791 | 0.735 | `low` | **90.5%** |
| `macro` | $[5000, \infty)$ | **0.22%** | 0.539 | 0.493 | 0.516 | `low` | **90.5%** |

- **Country-Level Coverage:** Across all 192 country-months (120 forward + 72 backward), empirical coverage under macro bounds is **98.4%**.
- **Reliability Rule:** Half-width $\le 0.20 \implies \text{high}$; $\le 0.45 \implies \text{medium}$; otherwise $\text{low}$. When $\hat{y} < 10$, reliability is $\text{insufficient}$ and intervals are suppressed.

---

## 5. Serving Analytics

### 5.1 Baseline & Current-vs-Median Calculations
- **Baseline Period:** Uses complete, non-provisional historical years (2012–2025).
- **Exact-Day Matching for Partial Months:** When the target month is partial (e.g., November 1–9), historical baseline years are aggregated strictly over days 1–9.
- **Quantiles:** Pre-computed and dynamic calculation of `median`, `q25`, and `q75`.
- **Static Contamination Warning:** When the share of NRT detections occurring in cells with no archive vegetation history exceeds $0.20\%$, a `possible_static_contamination` warning is attached to the API envelope.

