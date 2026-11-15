"""Application settings loaded from environment variables and .env file.

All secrets (FIRMS_MAP_KEY) and paths come from the environment only.
Never hard-code values here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_THIS_FILE = Path(__file__).resolve()
_BACKEND_DIR = _THIS_FILE.parent.parent  # backend/


class Settings(BaseSettings):
    """TerraFlare core backend settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- identity -------------------------------------------------------
    app_name: str = "TerraFlare API"
    api_version: str = "v1"
    api_prefix: str = "/api/v1"

    # ---- secrets (never logged, never committed) -------------------------
    firms_map_key: str | None = Field(default=None, alias="FIRMS_MAP_KEY")

    # ---- data -----------------------------------------------------------
    data_dir: Path = Field(
        default=Path("../data"),
        alias="TERRAFLARE_DATA_DIR",
    )
    # fixture = always synthetic; real = parquet files must exist
    data_mode: str = Field(default="fixture", alias="TERRAFLARE_DATA_MODE")
    data_version: str = Field(default="dev-0", alias="TERRAFLARE_DATA_VERSION")

    # ---- CORS -----------------------------------------------------------
    cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    # ---- advanced feature toggles (kept for backward compat) -----------
    enabled_features: tuple[str, ...] = (
        "season-shift",
        "fire-memory",
        "anomaly",
        "events",
        "exposure",
        "quality",
    )
    max_range_days: int = 3660
    default_limit: int = 500
    max_limit: int = 5000
    random_seed: int = 42

    # ---- season shift ---------------------------------------------------
    season_smooth_days: int = 7
    season_onset_pct: float = 10.0
    season_end_pct: float = 90.0
    season_baseline_n_years: int = 5
    season_recent_n_years: int = 3
    season_min_years_per_period: int = 3
    season_min_total_activity: float = 1.0
    season_bootstrap_n: int = 1000
    season_ci_level: float = 0.95

    # ---- fire memory ----------------------------------------------------
    memory_recent_window_years: int = 5
    memory_min_years: int = 4
    memory_high_recurrence: float = 0.6
    memory_strong_trend: float = 0.25
    memory_emerging_early_max: float = 0.5
    memory_drop_ratio: float = 0.5
    memory_min_activity: float = 1.0

    # ---- anomaly --------------------------------------------------------
    anomaly_period_days: int = 7
    anomaly_window_days: int = 7
    anomaly_min_baseline_years: int = 3
    anomaly_z_flag: float = 3.0
    anomaly_top_k: int = 5
    anomaly_max_explain_days: int = 92

    # ---- events ---------------------------------------------------------
    events_eps_km: float = 5.0
    events_time_scale_km_per_day: float = 2.0
    events_min_samples: int = 3
    events_min_detections: int = 3
    events_default_window_days: int = 30
    events_max_window_days: int = 120
    events_max_points: int = 50000

    # ---- exposure -------------------------------------------------------
    exposure_buffer_km: float = 5.0
    exposure_max_points: int = 50000

    # ---- quality --------------------------------------------------------
    quality_min_gap_days: int = 3
    quality_gap_quantile: float = 0.95
    quality_max_gaps: int = 50

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            # If formatted as JSON array like '["http://..."]'
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            # If formatted as comma-separated or plain string like 'http://localhost:5173'
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("data_dir", mode="before")
    @classmethod
    def _resolve_data_dir(cls, v: object) -> Path:
        p = Path(str(v))
        if not p.is_absolute():
            # Resolve relative to backend/ directory
            p = (_BACKEND_DIR / p).resolve()
        return p

    @field_validator("data_mode")
    @classmethod
    def _validate_data_mode(cls, v: str) -> str:
        allowed = {"fixture", "real", "auto"}
        if v not in allowed:
            raise ValueError(f"data_mode must be one of {allowed}, got '{v}'")
        return v


settings = Settings()

