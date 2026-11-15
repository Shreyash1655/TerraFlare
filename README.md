# TerraFlare

MODIS and VIIRS fire-detection harmonization and analysis for India, built on NASA FIRMS data (NASA Space Apps 2026).

TerraFlare ingests satellite hotspot detections, puts them on a common H3 grid, checks which days each satellite actually covered, and serves the results through a FastAPI backend to a React dashboard.

> A hotspot is a satellite-observed **thermal anomaly**, not a unique fire.

---

## 1. Scientific rules (hard constraints)

Every part of the code and UI must follow these.

1. **Never fabricate data.** Missing values show as `null` or "not available", never `0`.
2. **Never add raw MODIS and VIIRS counts.** The sensors differ in resolution (1 km vs 375 m) and sensitivity. They are shown side by side.
3. **Never infer coverage from the absence of hotspots.** Coverage comes only from the date ranges of ingested files.
4. **Avoid double-counting.**
5. **Keep NRT and SP separate**, and keep provenance on every output.
   - SP = Standard Processing (historical, science quality)
   - NRT = Near Real-Time (provisional)
6. **No synthetic fixture is ever shown as NASA data.**
7. **Document assumptions in the method text.**

Also do not: silently change the 1000-detection gates or the single-reference-platform rule, claim success from HTTP 200 alone (verify against the parquet), or run `load_hack.py`.

---

## 2. What the data is

- **Region:** India only. The single region `global` has bbox `[68.45, 8.05, 97.21, 34.97]` and is labelled "India (ingested FIRMS data)".
- **Sensors:** VIIRS (NOAA-20 / J1 is the reference platform) and MODIS (Terra and Aqua).
- **Footprint rule:** NRT rows are kept only in H3 resolution-5 cells that contain at least one SP detection (12,108 cells). So every map and total describes that footprint, not all of India.

### Ingested files (`backend\data\raw\firms`)

| Source | Type | Sensor | Range | Rows (clean) |
|---|---|---|---|---|
| J1_VIIRS_C2_SP_India_2021 to 2025 | SP | VIIRS | 2021-01-01 to 2026-01-01 | 775,165 / 612,676 / 591,760 / 586,325 / 664,542 |
| MODIS_C6_1_SP_India_2021 to 2025 | SP | MODIS | same | 113,295 / 82,583 / 78,602 / 75,434 / 96,405 |
| J1_VIIRS_C2_NRT_India_2026a | NRT | VIIRS | 2026-08-01 to 2026-10-14 | 17,900 |
| J1_VIIRS_C2_Custom_20261015_20261113 | NRT | VIIRS | 2026-10-15 to 2026-11-13 | 37,327 |
| J2_VIIRS_C2_Global_48h | NRT | VIIRS | 2026-11-11 to 2026-11-13 | 5,461 |
| MODIS_C6_1_NRT_India_2026a | NRT | MODIS | 2026-09-01 to 2026-10-14 | 1,476 |
| MODIS_C6_1_Custom_20261015_20261113 | NRT | MODIS | 2026-10-15 to 2026-11-13 | 9,681 |

Total: 3,748,632 rows (SP 3,676,787, NRT 71,845).

### Known data gap

- **No VIIRS data for 2026-01-02 to 2026-08-01**, and no MODIS data up to 2026-08-31.
- The cause is unconfirmed: either SP for 2026 is not yet released, or a download was truncated.
- These days stay **null** everywhere. They are never filled with zeros, NRT or interpolation.
- To close the gap: download J1 VIIRS SP and MODIS SP for India (2026-01-01 onward) from FIRMS Archive Download. Back up `data\` first. Re-run ingest, `build_coverage.py` and calibration. Where SP and NRT overlap, SP replaces NRT. Never sum them.

---

## 3. Architecture

```
FIRMS CSV files
   -> ingest (firms_ingest.py, adapt.py)  -> staging/obs_clean.parquet
   -> harmonization (calibration.py)      -> marts/harmonized_cell_day.parquet
                                          -> marts/calibration_models.parquet
                                          -> marts/frp_calibration_models.parquet
   -> build_coverage.py                   -> marts/coverage_day.parquet
   -> FastAPI (backend\app)  ->  React/TS + Vite (frontend)
```

### Data directories

`TERRAFLARE_DATA_DIR` (see section 4) points to `TerraFlare\data`:

| Path | Contents |
|---|---|
| `data\obs_clean.parquet` | Root copy read by the legacy repository (155 MB) |
| `data\staging\obs_clean.parquet` | Staging copy read by the DuckDB views |
| `data\marts\harmonized_cell_day.parquet` | Harmonized mart: 1,315,631 rows, 2021-01-01 to 2026-11-14 |
| `data\marts\calibration_models.parquet` | Count calibration (v1.2.0) |
| `data\marts\frp_calibration_models.parquet` | FRP calibration |
| `data\marts\coverage_day.parquet` | Per-sensor per-day coverage from file ranges |
| `data\harmonized_cell_day.parquet` | Root copy read by the legacy repository |

Important: two repositories exist.
- **Legacy `DataRepository`** (`app\utils\data_repository.py`) reads **root** files `data\{name}.parquet`. Almost every route uses it, including `/regions`, `/calendar`, `/hotspots`, season-shift, fire-memory and quality.
- **`DuckDBRepository`** reads views over `staging\` and `marts\`.

If you update a mart, copy it to the root as well, and restart uvicorn (some routes cache results).

### Backups (never delete)

`..\data_bak_14-11`, `..\proc_bak_14-11`, `app\data\processed\firms_bak_nrt`, `data_BACKUP`, `data_hackathon_bak_prev`. Stale files are renamed with a `.stale-15-11` suffix, not deleted.

---

## 4. Setup and running

Commands are for Windows PowerShell 5 (it has no `Select-String -Recurse`; use `Get-ChildItem -Recurse | Select-String`).

### Backend

```powershell
cd C:\Users\shrey\TerraFlare\backend
# activate the venv, then:
$env:TERRAFLARE_DATA_DIR = "C:\Users\shrey\TerraFlare\data"; uvicorn app.main:app --port 8000
```

Rules:
- `TERRAFLARE_DATA_DIR` **must be set in the same window that starts uvicorn.** Without it, `data_dir` falls back to `backend\app\data\processed` and every legacy route fails with `dataset_unavailable: obs_clean`.
- To set it permanently for new windows: `setx TERRAFLARE_DATA_DIR "C:\Users\shrey\TerraFlare\data"`.
- **Never set `TERRAFLARE_OBS_SOURCE`.** It switches the app to a single-file NRT repository and breaks every view. If the top bar shows "firms_nrt", run `Remove-Item Env:TERRAFLARE_OBS_SOURCE` and restart.
- Old uvicorn processes keep their old environment. Check with `Get-Process python` and stop leftovers before restarting.
- Restart uvicorn after any backend code change or data copy.

### Frontend

```powershell
cd C:\Users\shrey\TerraFlare\frontend
npm run dev
npx --no-install tsc -b     # type check; should print nothing
```

The frontend uses live data unless `VITE_API_MODE=mock`. Mock data is flagged `is_synthetic: true`.

### Tests

```powershell
cd C:\Users\shrey\TerraFlare\backend
Remove-Item Env:TERRAFLARE_DATA_DIR -ErrorAction SilentlyContinue
Remove-Item Env:TERRAFLARE_OBS_SOURCE -ErrorAction SilentlyContinue
python -m pytest -q
```

Run tests in a window **without** those variables so they stay in fixture mode. Last recorded result: 32 passed (before the later dashboard edits; re-run).

---

## 5. API

Base: `http://127.0.0.1:8000/api/v1`

| Path | Purpose |
|---|---|
| `/regions` | Region list (one region, India) |
| `/calendar?year=` | Daily NOAA-20 VIIRS counts from the mart, gated by coverage |
| `/history/yearly`, `/history/monthly`, `/history/current-vs-median` | Legacy FRP-based history for one product |
| `/hotspots`, `/hotspots/cells` | Raw detections and H3 cell aggregates |
| `/harmonization/comparison?granularity=day\|week\|month` | MODIS vs VIIRS vs harmonized series |
| `/harmonization/method` | Method text, validation metrics, assumptions |
| `/harmonization/coverage` | Per-year coverage, gaps, suspect-zero days |
| `/harmonization/frp-calibration` | FRP ratios (diagnostic only) |
| `/advanced/season-shift` | Fire-season timing and shift |
| `/advanced/fire-memory/cells`, `/advanced/fire-memory/cells/{id}/timeline` | Recurrence classes per H3 cell |
| `/advanced/anomalies`, `/advanced/events`, `/advanced/exposure` | Anomaly, cluster, exposure modules |
| `/advanced/quality`, `/advanced/quality/provenance` | Confidence and source lineage |
| `/advanced/health` | Status and data mode |

Verify an endpoint with:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/regions" | ConvertTo-Json -Depth 6
```

A page rendering or an HTTP 200 does not prove the data is valid. Check the payload and the parquet.

---

## 6. Method summary

### Harmonization

- The harmonized series **equals the NOAA-20 VIIRS observation** (identity, no interval). No MODIS conversion enters the mart.
- NOAA-21 appears in cell-days but is excluded from the mart.
- Reliability shows `provisional` when NRT rows are included.

### Calibration (SP only, cell-day grain, `calibration_models.parquet` v1.2.0)

| Platform | Ratio | Temporal holdout rel. MAE | Spatial holdout rel. MAE |
|---|---|---|---|
| Terra | 22.9149 | 15.5% | 48.1% |
| Aqua | 10.5798 | 7.6% | 49.4% |

- The ratios are stable over time but transfer poorly to unseen areas.
- In-sample bias is exactly 0. That is an estimator identity, not accuracy.
- The bootstrap interval (±4 to 6%) describes only the aggregate ratio.
- Selected grain: `cell_week`, chosen by held-out error.
- There is no S-NPP / NOAA-20 overlap, so the bridge is unfitted (`bridge_ratio` 1.0 is a default, not an estimate).
- FRP ratios (NOAA-20 per MODIS): Terra 2.103, Aqua 1.0583. Less reliable than counts; **not applied to the mart**.

### Coverage

- Built from the date ranges of ingested files, never from detection counts.
- Covered days: VIIRS 1,923, MODIS 1,892, both 1,885.
- **Suspect-zero days** (inside a file range but zero detections, treated as missing): VIIRS 2023-07-20 to 22, 2023-09-30, 2023-10-01, 2024-02-04, 2024-02-05. The 2023-07-20 to 22 run may be a real outage; it is not verified against NOAA-20 notices.
- Partial edge days (treated as missing): 2021-01-01, 2026-01-02, 2026-08-01, 2026-11-14.

### Season shift

- Onset = day 10% of the year's activity is reached; end = day 90%; peak = busiest smoothed day (7-day smoothing).
- Missing days are NaN, not zero. A year with more than **14 missing days** is partial and excluded.
- Defaults: baseline 5 years, recent 3 years, minimum 3 years per period, 1000 bootstrap draws, 95% interval.
- Result today: baseline 2021 to 2025 and recent 2023 to 2025 overlap, so evidence is labelled `insufficient_evidence` by design. Onset shift -7 days (CI -18 to 7), end shift +5 days (CI -9 to 14); both intervals include zero.
- Five seasons is short for a shift claim.

### Fire memory

- Cell-by-year activity matrix; classes: persistent, emerging, declining, sporadic.
- Incomplete years (more than 14 uncovered days, such as 2026) are excluded, not counted as zero.
- With 5 complete years the early period is a single year (2021), so "declining" and "emerging" are weakly supported.
- Theil-Sen slopes are vectorised (the earlier per-cell version took about 35 s).

### Assumptions introduced by the project team (document in any report)

- The 14-day threshold for an "incomplete" year. It appears in `season_shift_service.py` (`MAX_MISSING_DAYS`), `fire_memory_service.py` (`MAX_MISSING_DAYS`) and `DashboardPage.tsx` (`MAX_MISSING`). Keep these in sync.
- A covered day with no mart row is a real 0 (valid for the India-wide footprint).

---

## 7. Dashboard pages

| Page | What it shows |
|---|---|
| Geospatial Map (`/`) | Fire overview: VIIRS and MODIS totals by year (never summed), monthly chart with gaps, yearly table, cell and raw tables |
| Harmonization & Calibration | Comparison chart with shaded gaps and NRT marker, provenance, coverage table, FRP table, validation items |
| Climatology Calendar | Daily NOAA-20 VIIRS heatmap; dashed cells are missing data; amber ring marks provisional NRT days; no baseline comparison (none exists) |
| Advanced Intelligence | Season shift (plain-language), fire memory, anomaly, cluster and exposure tabs |
| Quality & Pipeline | Coverage, per-sensor confidence, raw counts per sensor, provenance table |

Frontend notes:
- Failed requests throw `{error:{message}}`, which is not an `Error`. Use the `errText()` helper (see `ComparisonPage.tsx`), not `err instanceof Error`, or the real server message is swallowed.
- Empty values display "not available", never 0.

---

## 8. Status

Phases: 0 audit (done), 1 calibration and validation fixes (done), 2 dashboard (in progress), 3 tests (not started).

### Verified

- Comparison page, provenance and coverage numbers (screenshots and API).
- Calendar API mart path (null gap days, provisional flags).
- Season-shift API (2021 to 2025 `ok`, 2026 `partial`) and the new sensor label.
- Fire-memory API ran (about 35 s) before the rewrite.
- pytest 32 passed, before the later edits.

### Applied but not yet visually or functionally confirmed

- `ComparisonPage.tsx` gap-filled chart, `CalendarPage.tsx`, `QualityPage.tsx`, `DashboardPage.tsx` layout (right-edge cut-off), `HotspotMapPage.tsx` popup "Processing" line, `fire_memory_service.py` speed and results, `SeasonShiftPage.tsx` plain-language page.
- TypeScript: an error was reported on `comparison?.evidence === 'interval_excludes_zero'` in `SeasonShiftPage.tsx`. Fix by widening the `evidence` type in `src\api\types\advanced.ts` or comparing via a `string` variable.

### Known defects, not fixed

1. `quality_service.py` `_availability` infers gaps from absent detections (breaks rule 3). The new page does not use it.
2. `quality_service.py` `_contribution` computes shares that sum MODIS and VIIRS. The new page does not use it.
3. `FireMemoryPage.tsx` swallows the server's real error and shows "needs more history" when the request actually failed.
4. Anomaly, Events and Exposure services have not been audited; they likely share the zero-fill and single-source issues.
5. `MethodDrawer.tsx` has not been checked for hardcoded method text.
6. 2026-10-14 (1,339 detections vs 732 the next day) falls at a file seam and is unchecked.
7. The calendar `_unit()` fallback labels FRP as "NRT" regardless of source.
8. `/hotspots` point endpoint (`routes_core\hotspots.py`) swallows query errors.
9. A covered day with no detections in a small selected area has no mart row, so a period can show null where 0 is correct (needs a per-period coverage query).
10. Mojibake (`Â°`, `Ã—`) in an `api_envelope.py` message; hardcoded fallback data version `2026.11.10.7`.
11. Season Shift page has hardcoded caveats ("2026 is incomplete", "periods overlap") that become wrong once SP data is added.
12. The root `data\harmonized_cell_day.parquet` is 697 KB while the mart is 6.7 MB, with the same row count and range. The size difference is unexplained; compare columns and values before trusting it.
13. It is unconfirmed whether `region_id: "global"` actually filters the mart.

### Next steps

1. Run `npx --no-install tsc -b` and fix any errors.
2. Restart uvicorn and re-verify fire-memory timing and season-shift output.
3. Fix `FireMemoryPage.tsx` error handling; check the request timeout in `client.ts`.
4. Re-run pytest (a test may assert the old region name).
5. Audit Anomaly, Events, Exposure and `MethodDrawer.tsx`.
6. Close the Jan to Aug 2026 data gap (section 2).
7. Phase 3 tests: coverage logic, null handling, season-shift NaN handling, fire-memory incomplete-year exclusion, calibration holdout and insufficient state, res-5 default in `resolve_api_area`, `/coverage` and `/frp-calibration` routes, and a guard that NRT and SP are never mixed in calibration.

---

## 9. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Dataset 'obs_clean' is not available` | uvicorn started without `TERRAFLARE_DATA_DIR`. Set it and restart from that window. |
| Top bar says `firms_nrt`, one-file views | `TERRAFLARE_OBS_SOURCE` is set. Remove it and restart. |
| Region still reads "Global (NASA FIRMS NRT)" | Backend not restarted since `routes\core.py` changed. |
| Page shows old data after a data copy | Results are cached; restart uvicorn. |
| Port 8000 busy or odd behaviour | `Get-Process python`, stop leftover processes. |
| Fire Memory says "needs more history" | Often a failed or slow request, not missing data. Check the API directly. |
| `python -c` fails with nested quotes | Write the script to `$env:TEMP\x.py` with a here-string and run it. |

---

## 10. Contributing rules

- Provide the full file when fixing a file; do not guess code you have not read.
- Do not overwrite or delete data or backups; rename stale files with a `.stale-15-11` suffix.
- Do not claim success from HTTP 200. Verify against the parquet.
- Per-phase final report: data source, observation count, date range, reliability, exact files changed, test results.

**Project demonstration:** [Watch the demo video](https://drive.google.com/file/d/1mqMYXPMp2-2OLNoxf-BVvSv9UWakWuoe/view?usp=sharing)
