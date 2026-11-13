# TerraFlare Core API Deployment Guide

This guide documents the procedures for packaging, shipping, configuring, and running the TerraFlare Core API in a production serving environment.

---

## 1. Architecture Overview

TerraFlare is designed as a high-performance, stateless REST API served via **FastAPI** backed by embedded **DuckDB** and columnar **Parquet marts**.
In production serving mode (`TERRAFLARE_DATA_MODE=real`), the API reads pre-aggregated analytical marts in read-only mode, providing sub-second latency across all spatial and historical queries without external database dependencies.

---

## 2. Packaging Serving Data (`data_serving/`)

The raw pipeline staging directory contains tens of gigabytes of raw sensor records and staging tables that are not required for serving.
To create a minimal, self-contained serving package:

```bash
# Package only required marts, DuckDB database, and manifest
python scripts/package_serving_data.py --src-dir data --dest-dir data_serving
```

### Included Serving Files
| File / Directory | Purpose | Access Mode |
| :--- | :--- | :---: |
| `manifest.json` | Dataset version, capabilities, sensor metadata, and boundaries | Read-only |
| `terraflare.duckdb` | Embedded analytical database with pre-indexed views | Read-only |
| `marts/harmonized_cell_day.parquet` | Daily H3 resolution-6 harmonized fire activity mart | Read-only |
| `marts/monthly_activity.parquet` | Pre-computed national and regional monthly aggregates | Read-only |
| `marts/calibration_models.parquet` | Fitted model parameters, strata ratios, and bootstrap errors | Read-only |
| `marts/cleaning_report.parquet` | Source-level ingestion and QC screening audit logs | Read-only |
| `marts/ingest_log.parquet` | Processing stream audit records | Read-only |
| `marts/cell_month_activity.parquet` | Pre-aggregated monthly cell mart for accelerated queries | Read-only |

### Shipping the Serving Bundle
Package `data_serving/` into a compressed archive or sync it directly to your target host:

```bash
# Option A: Tarball for container build or artifact storage
tar -czvf terraflare_serving_$(date +%Y%m%d).tar.gz -C data_serving .

# Option B: S3 / GCS cloud bucket sync
aws s3 sync data_serving/ s3://my-terraflare-bucket/data_serving/

# Option C: Direct rsync to remote host
rsync -avz --progress data_serving/ user@remote-host:/opt/terraflare/data_serving/
```

---

## 3. Environment Variables

Configure the API via the following environment variables (or a non-committed `.env` file):

| Variable | Type | Default | Required? | Description |
| :--- | :---: | :---: | :---: | :--- |
| `TERRAFLARE_DATA_DIR` | String | `data` | **Yes** (in prod) | Absolute or relative path to serving directory (e.g. `data_serving` or `/opt/terraflare/data_serving`). |
| `TERRAFLARE_DATA_MODE` | String | `real` | **Yes** (in prod) | Data source mode: `real` loads Parquet/DuckDB marts; `fixture` loads lightweight test fixtures. |
| `CORS_ORIGINS` | String | `http://localhost:5173` | Recommended | Comma-separated or JSON list of allowed origins (e.g. `http://localhost:5173,https://terraflare.example.com`). |
| `PORT` | Integer | `8000` | Optional | Port for the Uvicorn ASGI server to bind. |
| `HOST` | String | `0.0.0.0` | Optional | Host IP for ASGI server binding. |
| `WORKERS` | Integer | `4` | Optional | Number of Uvicorn worker processes (recommend 2–4). |

---

## 4. Starting the Server

From the repository root (`d:\TerraFlare` or deployment directory):

### Local / PowerShell
```powershell
$env:TERRAFLARE_DATA_DIR = "data_serving"
$env:TERRAFLARE_DATA_MODE = "real"
$env:CORS_ORIGINS = "http://localhost:5173,https://terraflare.example.com"

backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 2
```

### Linux / Container Entrypoint
```bash
export TERRAFLARE_DATA_DIR="/opt/terraflare/data_serving"
export TERRAFLARE_DATA_MODE="real"
export CORS_ORIGINS="http://localhost:5173,https://terraflare.example.com"

uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 4
```

---

## 5. Deployment Verification & Health Check

After launching the service, verify operations using `curl` or the automated smoke test:

```bash
# 1. Health Probe
curl -s http://localhost:8000/api/v1/health | jq .

# Expected Output:
# {
#   "status": "healthy",
#   "data_mode": "real",
#   "database": "connected"
# }

# 2. Capabilities & Version Metadata
curl -s http://localhost:8000/api/v1/meta/capabilities | jq .meta

# 3. Comprehensive End-to-End Smoke Test
python scripts/smoke_test.py
```

---

## 6. Dockerfile Reference

```dockerfile
FROM python:3.11-slim

WORKDIR /opt/terraflare

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend backend
COPY config config
COPY scripts scripts

# Copy pre-packaged serving data
COPY data_serving data_serving

# Set environment
ENV TERRAFLARE_DATA_DIR=/opt/terraflare/data_serving
ENV TERRAFLARE_DATA_MODE=real
ENV CORS_ORIGINS=http://localhost:5173
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

