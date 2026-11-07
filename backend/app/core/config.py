from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/app


def _csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in os.getenv(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = "TerraFlare API"
    api_version: str = "v1"

    # ---- data ----------------------------------------------------------
    data_dir: Path = Path(os.getenv("TERRAFLARE_DATA_DIR", BASE_DIR / "data" / "processed"))
    # auto  = real parquet files if present, otherwise synthetic fixture
    # real  = parquet files only (fails at startup if missing)
    # fixture = always synthetic
    data_mode: str = os.getenv("TERRAFLARE_DATA_MODE", "auto")
    data_version: str = os.getenv("TERRAFLARE_DATA_VERSION", "dev-0")

    # ---- API -----------------------------------------------------------
    cors_origins: tuple[str, ...] = _csv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    enabled_features: tuple[str, ...] = _csv(
        "ENABLED_ADVANCED_FEATURES", "season-shift,fire-memory,anomaly,events,exposure,quality"
    )
    max_range_days: int = 3660
    default_limit: int = 500
    max_limit: int = 5000
    random_seed: int = 42

    # ---- 1. season shift ----------------------------------------------
    season_smooth_days: int = 7
    season_onset_pct: float = 10.0
    season_end_pct: float = 90.0
    season_baseline_n_years: int = 5
    season_recent_n_years: int = 3
    season_min_years_per_period: int = 3
    season_min_total_activity: float = 1.0
    season_bootstrap_n: int = 1000
    season_ci_level: float = 0.95

    # ---- 2. fire memory -----------------------------------------------
    memory_recent_window_years: int = 5
    memory_min_years: int = 4
    memory_high_recurrence: float = 0.6
    memory_strong_trend: float = 0.25        # |slope| / mean annual activity
    memory_emerging_early_max: float = 0.5   # max recurrence in the early period
    memory_drop_ratio: float = 0.5           # recent mean <= ratio * early mean -> declining
    memory_min_activity: float = 1.0         # total activity below this = noise cell

    # ---- 3. anomaly ----------------------------------------------------
    anomaly_period_days: int = 7
    anomaly_window_days: int = 7             # +/- seasonal window around the period
    anomaly_min_baseline_years: int = 3
    anomaly_z_flag: float = 3.0
    anomaly_top_k: int = 5
    anomaly_max_explain_days: int = 92

    # ---- 4. events -----------------------------------------------------
    events_eps_km: float = 5.0
    events_time_scale_km_per_day: float = 2.0
    events_min_samples: int = 3
    events_min_detections: int = 3
    events_default_window_days: int = 30
    events_max_window_days: int = 120
    events_max_points: int = 50000

    # ---- 5. exposure ---------------------------------------------------
    exposure_buffer_km: float = 5.0
    exposure_max_points: int = 50000

    # ---- 6. quality ----------------------------------------------------
    quality_min_gap_days: int = 3
    quality_gap_quantile: float = 0.95
    quality_max_gaps: int = 50


settings = Settings()