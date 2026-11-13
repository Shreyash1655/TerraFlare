# TerraFlare

NASA Space Apps 2026: Harmonization of MODIS and VIIRS Hot Spots. The backend merges MODIS (2000-) and VIIRS (2012-) fire hotspots for India into one series and serves it at /api/v1.

## Run the API (Windows PowerShell)
Needs Git, Python (3.14 was tested), about 1.5 GB free disk.

    git clone https://github.com/Shreyash1655/TerraFlare.git
    cd TerraFlare
    git switch advanced-backend
    cd backend
    py -3 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.lock.txt

1. Download terraflare_data_v1.zip from the Releases page and unzip it anywhere (for example D:/TerraFlare_data). It must contain manifest.json and a marts folder.
2. Copy .env.example to .env in backend/ and set:

    TERRAFLARE_DATA_DIR=D:/TerraFlare_data
    TERRAFLARE_DATA_MODE=real
    CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

3. From backend/ run: uvicorn app.main:app --reload --port 8000
4. Open http://localhost:8000/docs and http://localhost:8000/api/v1/health

The frontend calls http://localhost:8000/api/v1. Example responses for every endpoint are in contracts/examples/.

## Rules for the UI
- Show a Provisional badge when is_provisional is true and a Partial badge when is_partial is true.
- Draw confidence bands only where lower and upper are present (pre-2012 values and bridge months). Observed VIIRS months have none.
- Show meta.series, meta.reliability and every string in meta.warnings. Label value_type "estimated, extrapolated" as Estimated.
