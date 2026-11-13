# TerraFlare Data Dictionary

This document specifies the schemas, data types, value domains, nullability, and provenance of all datasets, analytical marts, and database views in TerraFlare.

---

## 1. Summary of Datasets & Marts

| Dataset / Table Name | Path / Storage | Grain | Primary Key / Index | Description |
| :--- | :--- | :--- | :--- | :--- |
| `obs_clean` | `data/staging/obs_clean.parquet` | Point observation | `obs_id` | Validated, quality-screened active fire detection records across all 5 satellite platforms. |
| `cell_day_activity` | `data/marts/cell_day_activity.parquet` | Sensor $\times$ Cell $\times$ Day $\times$ Diurnal | `(source_id, platform, h3_cell, date, day_night)` | Daily cell-level activity aggregation per instrument platform. |
| `harmonized_cell_day` | `data/marts/harmonized_cell_day.parquet` | Cell $\times$ Day $\times$ Diurnal | `(h3_cell, acq_date, day_night)` | Core harmonized active fire time series in single-platform VIIRS reference units. |
| `monthly_activity` | `data/marts/monthly_activity.parquet` | Region $\times$ Year-Month | `(region_id, year_month)` | Pre-computed monthly sums, uncertainty bounds, and partial/provisional flags. |
| `calibration_models` | `data/marts/calibration_models.parquet` | Platform | `platform` | Fitted calibration parameters, strata ratios, and bootstrap confidence intervals. |
| `cleaning_report` | `data/marts/cleaning_report.parquet` | Ingestion batch | `run_id` | Audit records of row screening, static masking, and validation counts. |
| `ingest_log` | `data/marts/ingest_log.parquet` | Source file | `source_id` | Ingestion history, file checksums, and stream classification (SP vs. NRT). |
| `manifest.json` | `data/manifest.json` | Pipeline release | `data_version` | Release metadata, data version, active date range, capabilities, and stream boundaries. |

---

## 2. Table Schemas

### 2.1 `obs_clean` (Point-Level Observations)
Stored at `data/staging/obs_clean.parquet`. Compression: `zstd`.

| Column | Type | Nullable | Domain / Examples | Description |
| :--- | :---: | :---: | :--- | :--- |
| `obs_id` | `VARCHAR(16)` | No | 16-character hex hash | Unique observation ID derived from SHA256 of coordinates, timestamp, and platform. |
| `source_id` | `VARCHAR` | No | `modis_c61`, `viirs_snpp`, `viirs_noaa20`, `viirs_noaa21` | Ingestion source identifier. |
| `sensor_family` | `VARCHAR` | No | `MODIS`, `VIIRS` | Sensor instrument family. |
| `platform` | `VARCHAR` | No | `Terra`, `Aqua`, `S-NPP`, `NOAA-20`, `NOAA-21` | Satellite platform name. |
| `processing_stream` | `VARCHAR` | No | `SP`, `NRT` | Processing pipeline: Standard Processing (archive) vs. Near-Real-Time. |
| `product_version` | `VARCHAR` | No | `6.1`, `2` | Instrument algorithm collection version. |
| `ingest_batch_id` | `VARCHAR` | No | UUID / batch string | Ingestion batch execution identifier. |
| `acq_date` | `DATE` | No | `2000-11-01` to `2026-11-09` | UTC acquisition date of satellite overpass. |
| `acq_time_utc` | `VARCHAR(4)` | No | `0000` to `2359` | 4-digit HHMM acquisition time in UTC. |
| `local_date` | `DATE` | No | `2000-11-01` to `2026-11-10` | Local solar calendar date computed from longitude (`acq_datetime_utc + lon / 15.0` hours). Across India (68°E to 97°E), this aligns with the local solar day cycle and agrees with IST on >99% of observations. |
| `local_time` | `VARCHAR(5)` | No | `00:00` to `23:59` | Local overpass time in HH:MM format (local solar time). |
| `lat` | `DOUBLE` | No | $6.5 \le \text{lat} \le 37.5$ | Latitude in WGS84 decimal degrees. |
| `lon` | `DOUBLE` | No | $68.0 \le \text{lon} \le 97.5$ | Longitude in WGS84 decimal degrees. |
| `h3_cell` | `VARCHAR(15)` | No | e.g. `86618e38fffffff` | H3 spatial index at Resolution 6 (~36 km² hexagon). |
| `day_night` | `VARCHAR(1)` | No | `D`, `N` | Diurnal flag: `D` = Day overpass, `N` = Night overpass. |
| `brightness_k` | `FLOAT` | Yes | $250.0 \le T_b \le 550.0$ | Primary fire channel brightness temperature in Kelvin. |
| `bright_t31_k` | `FLOAT` | Yes | $220.0 \le T_{31} \le 400.0$ | Thermal background brightness temperature in Kelvin. |
| `frp_mw` | `FLOAT` | Yes | $\ge 0.0$ | Fire Radiative Power in Megawatts (MW). |
| `confidence_raw` | `VARCHAR` | No | `0–100` (MODIS), `l/n/h` (VIIRS) | Original confidence reported in source CSV. |
| `confidence_class` | `VARCHAR` | No | `low`, `nominal`, `high` | Standardized confidence category. |
| `fire_type` | `VARCHAR` | Yes | `0` (veg), `2` (other static), `3` (offshore) | FIRMS archive land-cover fire classification. |
| `is_valid` | `BOOLEAN` | No | `true`, `false` | True if observation passes all QC boundary and format checks. |
| `qc_flags` | `VARCHAR` | Yes | Comma-delimited strings | QC rejection/warning tags (e.g. `possible_static_source`). |
| `static_masked` | `BOOLEAN` | No | `true`, `false` | True if cell matches static industrial/flare source mask. |

---

### 2.2 `cell_day_activity` (Daily Sensor Activity Mart)
Stored at `data/marts/cell_day_activity.parquet`.

| Column | Type | Nullable | Description |
| :--- | :---: | :---: | :--- |
| `source_id` | `VARCHAR` | No | FIRMS source identifier. |
| `sensor_family` | `VARCHAR` | No | `MODIS` or `VIIRS`. |
| `platform` | `VARCHAR` | No | `Terra`, `Aqua`, `S-NPP`, `NOAA-20`, or `NOAA-21`. |
| `h3_cell` | `VARCHAR(15)` | No | H3 Resolution 6 index. |
| `date` | `DATE` | No | Observation date (UTC). |
| `day_night` | `VARCHAR(1)` | No | `D` (Day) or `N` (Night). |
| `n_detections` | `INTEGER` | No | Total count of valid fire detections in cell on this day/diurnal period. |
| `n_high_conf` | `INTEGER` | No | Detections with `confidence_class == 'high'`. |
| `frp_sum_mw` | `DOUBLE` | No | Sum of Fire Radiative Power (MW). |
| `frp_max_mw` | `DOUBLE` | No | Maximum single-detection Fire Radiative Power (MW). |

---

### 2.3 `harmonized_cell_day` (Core Harmonized Mart)
Stored at `data/marts/harmonized_cell_day.parquet`.

| Column | Type | Nullable | Domain / Examples | Description |
| :--- | :---: | :---: | :--- | :--- |
| `h3_cell` | `VARCHAR(15)` | No | e.g. `86618e38fffffff` | H3 Resolution 6 index. |
| `acq_date` | `DATE` | No | `2000-11-01` to `2026-11-09` | UTC observation date. |
| `day_night` | `VARCHAR(1)` | No | `D`, `N` | Diurnal period (`D`=Day, `N`=Night). |
| `region_id` | `VARCHAR` | No | `all`, or regional identifier | Associated geographic bounding region. |
| `harmonized_value` | `DOUBLE` | No | $\ge 0.0$ | Harmonized fire count in VIIRS reference units. |
| `harmonized_lower` | `DOUBLE` | Yes | $\ge 0.0$ or `NULL` | Lower 90% uncertainty bound ($= \text{value}$ for observed). |
| `harmonized_upper` | `DOUBLE` | Yes | $\ge 0.0$ or `NULL` | Upper 90% uncertainty bound ($= \text{value}$ for observed). |
| `modis_observed` | `DOUBLE` | No | $\ge 0.0$ | Unified MODIS detection count (`modis_used`: Aqua if present, else Terra). |
| `modis_terra_observed` | `DOUBLE` | No | $\ge 0.0$ | Direct Terra detection count. |
| `modis_aqua_observed` | `DOUBLE` | No | $\ge 0.0$ | Direct Aqua detection count. |
| `viirs_observed` | `DOUBLE` | No | $\ge 0.0$ | Direct single-platform VIIRS reference count. |
| `viirs_platform` | `VARCHAR` | No | `S-NPP`, `NOAA-20`, `none` | Active VIIRS reference platform on this date. |
| `platform_used` | `VARCHAR` | No | `Aqua`, `Terra`, `S-NPP`, `NOAA-20` | Satellite platform supplying the reference or primary covariate. |
| `interval_level` | `FLOAT` | No | `0.9` | Credible interval nominal level (90%). |
| `method_id` | `VARCHAR` | No | `identity`, `stratified_ratio` | Method used (`identity` for VIIRS era; `stratified_ratio` for pre-VIIRS). |
| `value_type` | `VARCHAR` | No | `observed`, `estimated, extrapolated` | Value provenance: `observed` in VIIRS era; `estimated, extrapolated` for 2000–2011. |
| `is_provisional` | `BOOLEAN` | No | `true`, `false` | True if observation falls in near-real-time provisional period. |
| `calibration_version` | `VARCHAR` | No | `1.1.0` | Semantic version of calibration parameters. |
| `data_version` | `VARCHAR` | No | e.g. `2026.11.11.1` | Immutable pipeline release tag. |

---

### 2.4 `monthly_activity` (Aggregated Regional Mart)
Stored at `data/marts/monthly_activity.parquet`.

| Column | Type | Nullable | Description |
| :--- | :---: | :---: | :--- |
| `region_id` | `VARCHAR` | No | Geographic region (`all`, `north_india`, etc.). |
| `year_month` | `VARCHAR(7)` | No | Calendar month string formatted `YYYY-MM`. |
| `value_type` | `VARCHAR` | No | Value classification (`observed` or `estimated, extrapolated`). |
| `sensor_family` | `VARCHAR` | No | Sensor family (`VIIRS` or `MODIS`). |
| `value` | `DOUBLE` | No | Total monthly fire activity count. |
| `lower` | `DOUBLE` | Yes | 90% lower confidence bound. |
| `upper` | `DOUBLE` | Yes | 90% upper confidence bound. |
| `is_provisional` | `BOOLEAN` | No | True if month contains NRT observations. |
| `is_partial` | `BOOLEAN` | No | True if month has incomplete calendar day coverage. |
| `data_version` | `VARCHAR` | No | Pipeline data release version. |

---

### 2.5 `calibration_models` (Model Registry)
Stored at `data/marts/calibration_models.parquet`.

| Column | Type | Nullable | Description |
| :--- | :---: | :---: | :--- |
| `platform` | `VARCHAR` | No | Instrument platform (`Terra`, `Aqua`, `Joint`). |
| `target_sensor` | `VARCHAR` | No | Target reference sensor (`VIIRS`). |
| `method_id` | `VARCHAR` | No | Method (`stratified_ratio`, `count_regression`). |
| `global_ratio` | `DOUBLE` | No | Global pooled ratio across all strata. |
| `strata_ratios_json` | `VARCHAR` | No | JSON mapping of `(month_daynight)` keys to calibrated ratio factors. |
| `regression_params_json`| `VARCHAR` | No | JSON dictionary of fitted regression parameters. |
| `uncertainty_json` | `VARCHAR` | No | JSON dictionary of block-bootstrap uncertainty quantiles. |
| `n_cell_days_used` | `INTEGER` | No | Sample size of cell-days used during fitting. |

