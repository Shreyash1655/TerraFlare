# TerraFlare Backend Core Engine & API

High-performance, science-grade satellite active fire harmonization and analytical serving engine for NASA FIRMS observations (MODIS and VIIRS).

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.11 recommended)
- **PowerShell** (Windows) or **Bash** (Linux/macOS)
- **Git**

---

## 2. Setup & Installation (PowerShell)

From the repository root (`TerraFlare`):

```powershell
# 1. Create a virtual environment
python -m venv backend\.venv

# 2. Activate the virtual environment
backend\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install backend dependencies
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

---

## 3. Running the API Server

Start the FastAPI ASGI server using Uvicorn:

```powershell
# Set Python path to include backend/
$env:PYTHONPATH = "backend"

# Start development server with auto-reload
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Once running:
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc UI:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 4. Switching Data Modes: Fixture vs. Real

TerraFlare supports instant switching between high-speed isolated test fixtures and production analytical marts via the `TERRAFLARE_DATA_MODE` environment variable:

### Real Data Mode (Production Analytical Serving)
Reads from columnar Parquet marts and the embedded DuckDB analytical database (`data/` or `data_serving/`):

```powershell
$env:TERRAFLARE_DATA_MODE = "real"
$env:TERRAFLARE_DATA_DIR = "data"          # or "data_serving"
$env:CORS_ORIGINS = "http://localhost:5173"
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --port 8000
```

### Fixture Data Mode (Isolated Testing)
Loads pre-built, lightweight synthetic fixtures for fast deterministic local test execution without requiring the multi-gigabyte production dataset:

```powershell
$env:TERRAFLARE_DATA_MODE = "fixture"
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --port 8000
```

---

## 5. Running Tests & Smoke Verification

### Run Full Test Suite
```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/core/ backend/tests/contract/ -v
```

### Run Contract Tests
Validates that Core API response structures match the frontend contracts and schema definitions:
```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/contract/ -v
```

### Run Smoke Test & Latency Benchmark (Real Data)
Executes across all 16 API endpoints and boundary checks against real data, benchmarking response latencies:
```powershell
backend\.venv\Scripts\python.exe scripts/smoke_test.py
```

---

## 6. Code Quality & Linting

Run **Ruff** for high-speed Python linting and formatting validation:

```powershell
# Check for lint errors
backend\.venv\Scripts\ruff check backend/ scripts/

# Format check
backend\.venv\Scripts\ruff format --check backend/ scripts/
```

---

## 7. Packaging Serving Data

To package only the minimal serving marts into `data_serving/` for deployment:

```powershell
backend\.venv\Scripts\python.exe scripts/package_serving_data.py --dest-dir data_serving
```
See [docs/DEPLOY.md](file:///d:/TerraFlare/docs/DEPLOY.md) for complete production deployment details.

