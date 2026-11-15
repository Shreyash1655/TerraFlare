# TerraFlare

Satellite fire-activity dashboard for India. It harmonizes NASA FIRMS active-fire detections (MODIS and VIIRS) into one VIIRS NOAA-20 reference series, with coverage, provenance and uncertainty shown on every output.

Backend: FastAPI + DuckDB views over Parquet. Frontend: React + TypeScript (Vite).

## Scientific rules

- Hotspots are thermal anomalies, not unique fires.
- Missing data is shown as null or "not available", never 0.
- Raw MODIS and VIIRS counts are never added together.
- Coverage comes from ingested file date ranges, never from the absence of detections.
- NRT (near real-time) and SP (standard processing) are kept separate. SP replaces NRT on overlapping days; they are never summed.
- The harmonized series uses a single VIIRS reference platform (NOAA-20). Other VIIRS platforms are not summed.
- Calibration is fitted on SP data only.
- Years with more than 14 uncovered days, or not spanning 1 Jan to 31 Dec, are treated as incomplete and excluded from Season Shift and Fire Memory. The 14-day threshold is an analyst assumption, not a NASA value.

## Data (not in the repository)

Raw NASA FIRMS shapefiles and all Parquet/DuckDB files are git-ignored. Download them from the NASA FIRMS Archive Download page (India, VIIRS J1 and MODIS C6.1, SP and NRT) and place each dataset in its own folder:

    backend/data/raw/firms/<DATASET_NAME>/<DATASET_NAME>.shp (+ .shx .dbf .prj .cpg)

Current coverage: SP 2021-01-01 to 2026-07-31 (VIIRS) / 2026-08-01 (MODIS); NRT from 2026-08-01 (VIIRS) / 2026-09-01 (MODIS). MODIS 2026-08-02 to 2026-08-31 is a real gap and stays null.

## Data pipeline

Run from `backend/` with the venv active. Do not set `TERRAFLARE_OBS_SOURCE` for any of these.

    python -m app.services.firms_ingest process data\raw\firms
    python -m app.services.firms_export data\raw\firms
    python adapt.py
    python build_coverage.py
    python run_hack.py

Then copy into the data folder (back up first):

- `app/data/processed/firms/obs_clean.parquet` to `data/obs_clean.parquet`
- `app/data/processed/firms/coverage_day.parquet` and `data_hackathon/marts/*.parquet` to `data/marts/`

## Run the backend

    cd backend
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    $env:TERRAFLARE_DATA_DIR = "C:\path\to\TerraFlare\data"
    uvicorn app.main:app --port 8000

`TERRAFLARE_DATA_DIR` must be set in the same window that starts uvicorn. API docs: http://127.0.0.1:8000/docs

Main routes under `/api/v1`: `regions`, `calendar`, `hotspots`, `history/*`, `harmonization/{comparison,method,coverage,frp-calibration}`, `advanced/{season-shift,fire-memory/cells,quality,anomalies,events,exposure}`.

## Run the frontend

    cd frontend
    npm install
    npm run dev

API address is set in `frontend/.env.development` (`VITE_API_BASE_URL`). `VITE_API_MODE=mock` uses built-in sample data; see `frontend/.env.example` for the real-API setting.

## Tests

    cd backend
    pytest -q

Run with no environment variables set. Type-check the frontend with `npx --no-install tsc -b`.

## Known limitations

- India only. Calibration ratios are India-specific; spatial holdout error is about 45-47%.
- No S-NPP/NOAA-20 overlap exists, so no bridge is fitted.
- Fire Memory uses 2021-2025, so the early period is a single year and declining/emerging labels are weakly supported.
- FRP ratios are diagnostic only and are not applied to the harmonized series.

## Branches

- `advanced-frontend`: current working branch.
- `advanced-backend`: older backend with its own `tests/core`; not yet merged.
