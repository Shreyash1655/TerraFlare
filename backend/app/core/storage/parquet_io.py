"""Parquet I/O utilities and DuckDB synchronization for marts and staging datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.core.storage.schema_sql import create_views
from app.settings import settings


def write_parquet(
    df: pd.DataFrame,
    path: Path | str,
    index: bool = False,
) -> Path:
    """Write DataFrame to Parquet, ensuring parent directories exist."""
    p = Path(path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=index)
    return p


def read_parquet(
    path: Path | str,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Read a Parquet file or directory into a DataFrame."""
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Parquet file or directory not found: {p}")
    return pd.read_parquet(p, columns=columns)


def write_mart(
    df: pd.DataFrame,
    mart_name: str,
    data_dir: Path | None = None,
) -> Path:
    """Write DataFrame as a mart to data/marts/<mart_name>.parquet."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    marts_dir = base_data_dir / "marts"
    marts_dir.mkdir(parents=True, exist_ok=True)
    mart_file = marts_dir / f"{mart_name}.parquet"
    df.to_parquet(mart_file, index=False)
    return mart_file


def sync_duckdb_views(
    data_dir: Path | None = None,
    db_path: Path | None = None,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Connect to data/terraflare.duckdb and create or refresh views for all datasets."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    target_db = Path(db_path) if db_path else (base_data_dir / "terraflare.duckdb")
    target_db.parent.mkdir(parents=True, exist_ok=True)

    try:
        con = duckdb.connect(str(target_db), read_only=read_only)
    except Exception:
        con = duckdb.connect(str(target_db), read_only=True)
    if not read_only:
        try:
            create_views(con, base_data_dir)
        except Exception:
            pass
    return con

