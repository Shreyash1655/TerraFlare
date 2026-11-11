# TerraFlare Data Profile

This profile was automatically computed from real NASA FIRMS data sampled with `--sample 100000 --sample-mode spread` across all source archive and NRT files.

## Summary Metrics

- **Total Canonical Observations Processed:** 529,563
- **Valid Observations:** 420,910 (79.48%)
- **Invalid / Flagged Observations:** 108,653 (20.52%)
- **Global Acquisition Date Range:** `2000-11-01 00:00:00` to `2026-11-09 00:00:00`
- **S-NPP Maximum Acquisition Date:** `2026-11-02 00:00:00` (On or before 2 Nov 2026: **True**)
- **Stream / Filename Disagreements:** 0 (all rows match their file name pattern)

## Per-Source Date Range and Observation Counts

| Source ID | Sensor Family | Min Date | Max Date | Observations |
| :--- | :--- | :--- | :--- | :--- |
| `modis_c61` | MODIS | `2000-11-01 00:00:00` | `2026-11-09 00:00:00` | 108,711 |
| `viirs_noaa20` | VIIRS | `2018-04-01 00:00:00` | `2026-11-09 00:00:00` | 146,420 |
| `viirs_noaa21` | VIIRS | `2023-03-01 00:00:00` | `2026-11-09 00:00:00` | 142,853 |
| `viirs_snpp` | VIIRS | `2012-01-20 00:00:00` | `2026-11-02 00:00:00` | 131,579 |

## Storage Optimization Metrics (Item 8)

- **obs_clean File Size:** 14.84 MB (15,565,059 bytes)
- **Bytes per Row (Current - zstd, 16-char obs_id, extras dropped):** 29.39 B/row
- **Bytes per Row (Prior Baseline - snappy, unhashed obs_id, with extras):** 197.57 B/row
- **Storage Reduction:** 85.1% reduction per row
- **Cell-Day Runtime (Vectorized Pandas):** 1.72s

## Distribution by Processing Stream

| Processing Stream | Description | Rows | Percentage |
| :--- | :--- | :--- | :--- |
| `NRT` | Near Real-Time | 129,563 | 24.47% |
| `SP` | Standard Product (Archive) | 400,000 | 75.53% |

## Distribution by Day / Night

| Day/Night | Rows | Percentage |
| :--- | :--- | :--- |
| Daytime (D) | 376,314 | 71.06% |
| Nighttime (N) | 153,249 | 28.94% |

## Distribution by Fire Type

| Fire Type Code | Description | Rows |
| :--- | :--- | :--- |
| `0` | Presumed vegetation fire | 360,130 |
| `1` | Active volcano | 7 |
| `2` | Other static land source (gas flare / industrial) | 39,153 |
| `3` | Offshore detection | 710 |
| `None (NRT)` | Unspecified (NRT stream without type column) | 129,563 |

## Distribution by Confidence Class

| Confidence Class | Rows | Percentage |
| :--- | :--- | :--- |
| `high` | 27,884 | 5.27% |
| `low` | 70,638 | 13.34% |
| `nominal` | 431,041 | 81.40% |

## Cleaning & Validation Rules Flags

| Rule ID | Rows Flagged | Dropped | Description |
| :--- | :--- | :--- | :--- |
| `coordinate_range` | 0 | 0 | Latitude / longitude out of bounds |
| `missing_date` | 0 | 0 | Missing or unparseable acquisition date |
| `duplicate_obs_id` | 0 | 0 | Duplicate within-stream observation identity |
| `duplicate_across_streams` | 0 | 0 | Overlapping NRT detection matching existing SP row |
| `fire_type_filter` | 39,870 | 0 | Non-vegetation static / offshore source (type != 0) |
| `confidence_filter` | 70,638 | 0 | Confidence below configured threshold (nominal) |
| `negative_frp` | 0 | 0 | Negative Fire Radiative Power (FRP < 0) |
| `possible_static_source` | 43,972 | 0 | NRT row located in resolution-8 static mask cell |

### Audit Note on Prior Count Discrepancy (116,067 and 170,768)

In an earlier draft of this report, `fire_type_filter` reported 116,067 flagged rows and `confidence_filter` reported 170,768 flagged rows:
- **Exact Cause Identified**: Prior to run isolation, `cleaning_report.parquet` accumulated records across sequential pipeline invocations without per-run separation. Specifically, an earlier single-source run (`source_id == 'viirs_noaa20'`) had flagged 76,197 non-0 fire types and 100,130 sub-nominal confidences.
- When the profile script summed `rows_flagged` across all records in `cleaning_report.parquet` (`source_id == 'all'` plus `source_id == 'viirs_noaa20'`), the totals summed to:
  - `fire_type_filter`: 39,870 (current sample) + 76,197 (prior run) = **116,067**
  - `confidence_filter`: 70,638 (current sample) + 100,130 (prior run) = **170,768**
- **Hygiene & Verification (Task 7c)**: With per-run isolation, a `run_id` column is attached to `cleaning_report.parquet` and tables reflect only the current run. Furthermore, the cleaning pipeline now asserts count consistency: `fire_type_filter` (39,870) $\le$ actual rows with non-0 fire type (39,870), and `confidence_filter` (70,638) $\le$ actual rows with low confidence (70,638).

## Pipeline Stage Runtimes (--sample 100000)

| Stage | Runtime (seconds) |
| :--- | :--- |
| `ingest` | 19.07s |
| `clean` | 10.27s |
| `cell_day` | 1.72s |
| `harmonize` | 14.01s |
| `monthly` | 1.17s |
| **Total** | **46.72s** |
