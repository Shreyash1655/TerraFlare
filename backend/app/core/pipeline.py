"""TerraFlare data pipeline orchestrator.

Coordinates ingestion, cleaning, H3 spatial grid assignment, cell-day aggregation,
harmonization, monthly marts, DuckDB view synchronization, and dataset manifest creation.

Stages:
1. ingest: Reads raw FIRMS files, converts to canonical schema, writes data/raw/ and data/staging/obs_all/.
2. clean: Normalises confidence & solar local dates, evaluates cleaning rules, assigns H3 cells,
   writes data/staging/obs_clean.parquet and cleaning_report.parquet.
3. cell_day: Aggregates valid observations into cell_day_activity mart by platform, cell, date, day_night.
   Writes data/marts/cell_day_activity.parquet.
4. harmonize: Harmonizes MODIS and VIIRS activity (stub for now). Writes data/marts/harmonized_cell_day.parquet.
5. monthly: Computes monthly activity summaries (stub for now). Writes data/marts/monthly_activity.parquet.
6. manifest: Generates data/manifest.json with config hash, git SHA, row counts, and capabilities,
   and refreshes DuckDB views in data/terraflare.duckdb.
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.core.cleaning.normalize import normalize_canonical_dataframe
from app.core.cleaning.report import REPORT_COLUMNS, build_cleaning_report, clean_observations, save_cleaning_report
from app.core.cleaning.rules import apply_cleaning_rules
from app.core.harmonization.calibration import apply_calibration_to_cell_days, fit_calibration_suite
from app.core.harmonization.temporal import aggregate_cell_day_activity
from app.core.ingestion.ingest import ingest_all, ingest_file
from app.core.spatial.grid import assign_h3_cells
from app.core.storage.parquet_io import sync_duckdb_views, write_mart
from app.settings import settings
from app.shared.canonical import CANONICAL_COLUMNS
from app.shared.config_loader import get_harmonization_config, get_sources
from app.shared.regions import list_region_ids

logger = logging.getLogger("terraflare.pipeline")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# Metadata and Manifest Helpers
# -----------------------------------------------------------------------------


def compute_config_hash() -> str:
    """Compute SHA-256 hash across all configuration YAML files."""
    # Find config dir at repo root
    config_dir = Path(__file__).resolve().parents[3] / "config"
    if not config_dir.exists():
        return "unversioned_config"

    h = hashlib.sha256()
    yaml_files = sorted(config_dir.glob("*.yaml"))
    for yf in yaml_files:
        try:
            h.update(yf.name.encode("utf-8"))
            h.update(yf.read_bytes())
        except Exception:
            pass
    return h.hexdigest()


def get_git_commit() -> str | None:
    """Return the current git HEAD commit hash, or None if unavailable."""
    try:
        repo_root = Path(__file__).resolve().parents[3]
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
        )
        sha = res.stdout.strip()
        return sha if sha else None
    except Exception:
        return None


def compute_row_counts(data_dir: Path) -> dict[str, int]:
    """Count rows across raw, staging, and mart datasets using Parquet metadata."""
    import pyarrow.parquet as pq

    counts: dict[str, int] = {
        "raw": 0,
        "obs_all": 0,
        "obs_clean": 0,
        "cell_day_activity": 0,
        "harmonized_cell_day": 0,
        "monthly_activity": 0,
    }

    # 1. raw: sum from ingest_log
    log_path = data_dir / "staging" / "ingest_log.parquet"
    if log_path.exists():
        try:
            log_df = pd.read_parquet(log_path, columns=["rows_in"])
            counts["raw"] = int(log_df["rows_in"].sum())
        except Exception:
            pass
    elif (data_dir / "raw").exists():
        for p in (data_dir / "raw").glob("*/*.parquet"):
            try:
                counts["raw"] += pq.read_metadata(p).num_rows
            except Exception:
                pass

    # 2. obs_all
    obs_all_dir = data_dir / "staging" / "obs_all"
    if obs_all_dir.exists():
        for p in obs_all_dir.glob("*.parquet"):
            try:
                counts["obs_all"] += pq.read_metadata(p).num_rows
            except Exception:
                pass

    # 3. obs_clean
    obs_clean_path = data_dir / "staging" / "obs_clean.parquet"
    if obs_clean_path.exists():
        try:
            counts["obs_clean"] = pq.read_metadata(obs_clean_path).num_rows
        except Exception:
            pass

    # 4. cell_day_activity
    cell_day_path = data_dir / "marts" / "cell_day_activity.parquet"
    if cell_day_path.exists():
        try:
            counts["cell_day_activity"] = pq.read_metadata(cell_day_path).num_rows
        except Exception:
            pass

    # 5. harmonized_cell_day
    harm_path = data_dir / "marts" / "harmonized_cell_day.parquet"
    if harm_path.exists():
        try:
            counts["harmonized_cell_day"] = pq.read_metadata(harm_path).num_rows
        except Exception:
            pass

    # 6. monthly_activity
    monthly_path = data_dir / "marts" / "monthly_activity.parquet"
    if monthly_path.exists():
        try:
            counts["monthly_activity"] = pq.read_metadata(monthly_path).num_rows
        except Exception:
            pass

    return counts


def compute_date_range(obs_clean_path: Path) -> dict[str, str | None]:
    """Derive minimum and maximum dates from obs_clean dataset."""
    if not obs_clean_path.exists():
        return {"start": None, "end": None, "min_date": None, "max_date": None}
    try:
        df = pd.read_parquet(obs_clean_path, columns=["acq_date"])
        if df.empty or df["acq_date"].dropna().empty:
            return {"start": None, "end": None, "min_date": None, "max_date": None}
        min_d = str(df["acq_date"].min())
        max_d = str(df["acq_date"].max())
        return {"start": min_d, "end": max_d, "min_date": min_d, "max_date": max_d}
    except Exception:
        return {"start": None, "end": None, "min_date": None, "max_date": None}


def compute_capabilities(obs_clean_path: Path) -> dict[str, bool]:
    """Detect presence of optional feature fields in obs_clean."""
    default_caps = {
        "has_frp": True,
        "has_confidence": True,
        "has_day_night": True,
        "has_platform": True,
        "has_fire_type": True,
    }
    if not obs_clean_path.exists():
        return default_caps
    try:
        cols_to_check = {
            "frp_mw": "has_frp",
            "confidence_raw": "has_confidence",
            "day_night": "has_day_night",
            "platform": "has_platform",
            "fire_type": "has_fire_type",
        }
        df = pd.read_parquet(obs_clean_path, columns=list(cols_to_check.keys()))
        if df.empty:
            return default_caps
        caps = {}
        for col, cap_key in cols_to_check.items():
            if col in df.columns:
                caps[cap_key] = bool(df[col].notna().any())
            else:
                caps[cap_key] = False
        return caps
    except Exception:
        return default_caps


def determine_data_version(
    manifest_path: Path,
    config_hash: str,
    row_counts: dict[str, int],
    git_commit: str | None,
    explicit_version: str | None = None,
) -> str:
    """Return data_version, preserving existing version if data and config are unchanged."""
    if explicit_version:
        return explicit_version

    today_str = datetime.now(timezone.utc).strftime("%Y.%m.%d")

    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            # If config, git, and row counts are identical, re-use existing version (idempotent)
            if (
                old.get("config_hash") == config_hash
                and old.get("row_counts") == row_counts
                and old.get("git_commit") == git_commit
                and old.get("data_version")
            ):
                return str(old["data_version"])

            # Otherwise increment revision for today
            old_version = str(old.get("data_version", ""))
            if old_version.startswith(today_str):
                parts = old_version.split(".")
                if len(parts) >= 4 and parts[-1].isdigit():
                    rev = int(parts[-1]) + 1
                    return f"{today_str}.{rev}"
        except Exception:
            pass

    return f"{today_str}.1"


def compute_stream_boundaries(data_dir: Path) -> dict[str, dict[str, str]]:
    """Compute SP max date and NRT min date per source directly from the ingested data."""
    boundaries: dict[str, dict[str, str]] = {}
    obs_all_dir = data_dir / "staging" / "obs_all"
    if not obs_all_dir.exists():
        return boundaries

    import duckdb

    try:
        con = duckdb.connect()
        files = list(obs_all_dir.glob("*.parquet"))
        if files:
            files_sql = ", ".join(f"'{f.as_posix()}'" for f in files)
            df = con.execute(f"""
                SELECT
                    source_id,
                    MAX(CASE WHEN UPPER(processing_stream) = 'SP' THEN acq_date::VARCHAR END) AS sp_end,
                    MIN(CASE WHEN UPPER(processing_stream) = 'NRT' THEN acq_date::VARCHAR END) AS nrt_start
                FROM read_parquet([{files_sql}])
                GROUP BY source_id
            """).df()
            for _, r in df.iterrows():
                sid = str(r["source_id"])
                sp_e = str(r["sp_end"]) if pd.notna(r["sp_end"]) and r["sp_end"] is not None else None
                nrt_s = str(r["nrt_start"]) if pd.notna(r["nrt_start"]) and r["nrt_start"] is not None else None
                if sp_e or nrt_s:
                    boundaries[sid] = {}
                    if sp_e:
                        boundaries[sid]["sp_end_date"] = sp_e
                    if nrt_s:
                        boundaries[sid]["nrt_start_date"] = nrt_s
        con.close()
    except Exception:
        pass
    return boundaries


def write_manifest(
    data_dir: Path | None = None,
    data_version: str | None = None,
) -> dict[str, Any]:
    """Write data/manifest.json containing version, git commit, configs, row counts, and capabilities."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    manifest_path = base_data_dir / "manifest.json"

    conf_hash = compute_config_hash()
    git_sha = get_git_commit()
    row_counts = compute_row_counts(base_data_dir)
    version = determine_data_version(manifest_path, conf_hash, row_counts, git_sha, explicit_version=data_version)

    sources_cfg = get_sources()
    sources_meta = {}
    for sid, cfg in sources_cfg.items():
        sources_meta[sid] = {
            "sensor_family": cfg.get("sensor_family"),
            "product_version": cfg.get("product_version"),
            "processing_stream": cfg.get("processing_stream"),
            "enabled": cfg.get("enabled", True),
        }

    # Stream boundaries computed dynamically from data (Task 7g)
    stream_boundaries = compute_stream_boundaries(base_data_dir)

    h3_res = int(get_harmonization_config().get("h3_resolution", 6))
    regions_list = list(list_region_ids())
    obs_clean_p = base_data_dir / "staging" / "obs_clean.parquet"
    date_rng = compute_date_range(obs_clean_p)
    caps = compute_capabilities(obs_clean_p)

    manifest_data = {
        "data_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_sha,
        "sources": sources_meta,
        "stream_boundaries": stream_boundaries,
        "h3_resolution": h3_res,
        "config_hash": conf_hash,
        "row_counts": row_counts,
        "date_range": date_rng,
        "regions": regions_list,
        "capabilities": caps,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"Manifest written: {manifest_path} (data_version={version})")
    return manifest_data


# -----------------------------------------------------------------------------
# Pipeline Stage Implementations
# -----------------------------------------------------------------------------


def stage_ingest(
    source: str | None = None,
    year: int | str | None = None,
    sample: int | None = None,
    sample_mode: str = "first",
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute ingestion stage: raw CSVs -> raw parquet + canonical staging/obs_all/."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    logger.info(
        f"[STAGE: ingest] Starting (source={source}, year={year}, sample={sample}, mode={sample_mode})"
    )

    res = ingest_all(
        data_dir=base_data_dir,
        source_id_filter=source,
        sample_n=sample,
        sample_mode=sample_mode,
        year=year,
    )

    rows_in = res["total_rows"]
    rows_out = rows_in  # Ingest maps 1:1 raw to canonical observations
    logger.info(f"[STAGE: ingest] Finished. files={res['files_ingested']} | rows_in={rows_in} | rows_out={rows_out}")
    return {
        "stage": "ingest",
        "files_ingested": res["files_ingested"],
        "rows_in": rows_in,
        "rows_out": rows_out,
        "details": res["results"],
    }


def stage_clean(
    source: str | None = None,
    year: int | str | None = None,
    sample: int | None = None,
    data_dir: Path | None = None,
    run_id: str | None = None,
    clear_tables: bool = True,
) -> dict[str, Any]:
    """Execute cleaning stage: staging/obs_all/ -> staging/obs_clean.parquet + cleaning_report.parquet."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    obs_all_dir = base_data_dir / "staging" / "obs_all"
    actual_run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    logger.info(f"[STAGE: clean] Starting (source={source}, year={year}, sample={sample}, run_id={actual_run_id})")

    if not obs_all_dir.exists():
        logger.warning(f"No staging directory found at {obs_all_dir}")
        return {"stage": "clean", "rows_in": 0, "rows_out": 0, "valid_count": 0, "flagged_count": 0, "run_id": actual_run_id}

    # 1. Collect canonical parquet files
    files = sorted(obs_all_dir.glob("*.parquet"))
    if source:
        files = [f for f in files if f.name.startswith(f"{source}_") or source in f.name]

    if not files:
        logger.warning("No canonical observation files matched criteria.")
        return {"stage": "clean", "rows_in": 0, "rows_out": 0, "valid_count": 0, "flagged_count": 0, "run_id": actual_run_id}

    # 2. Process canonical observation files chunk-by-chunk using ParquetWriter for memory safety
    import pyarrow as pa
    import pyarrow.parquet as pq

    cleaned_chunks = []
    reports = []
    tot_rows_in = 0
    tot_valid = 0
    tot_flagged = 0

    obs_clean_file = base_data_dir / "staging" / "obs_clean.parquet"
    obs_clean_file.parent.mkdir(parents=True, exist_ok=True)

    writer = None
    target_schema = None

    for f in files:
        try:
            chunk = pd.read_parquet(f)
            if sample is not None and not chunk.empty:
                chunk = chunk.head(sample)
            if year is not None and not chunk.empty:
                years_set = {str(y) for y in year} if isinstance(year, (list, tuple, set)) else {str(year)}
                chunk = chunk[chunk["acq_date"].astype(str).str[:4].isin(years_set)]
            if chunk.empty:
                continue

            r_in = len(chunk)
            tot_rows_in += r_in
            sid = source or (chunk["source_id"].iloc[0] if "source_id" in chunk.columns else "all")

            cleaned_chunk, rep = clean_observations(
                chunk,
                source_id=sid,
                data_dir=base_data_dir,
                write_report=False,
                run_id=actual_run_id,
            )
            reports.append(rep)

            cleaned_chunk = assign_h3_cells(cleaned_chunk)
            if "obs_id" in cleaned_chunk.columns:
                cleaned_chunk["obs_id"] = [
                    hashlib.sha256(str(x).encode("utf-8")).hexdigest()[:16] if pd.notna(x) else ""
                    for x in cleaned_chunk["obs_id"]
                ]
            if "extras" in cleaned_chunk.columns:
                cleaned_chunk = cleaned_chunk.drop(columns=["extras"])

            tot_valid += int((cleaned_chunk["is_valid"] == True).sum())
            tot_flagged += int((cleaned_chunk["is_valid"] == False).sum())

            table = pa.Table.from_pandas(cleaned_chunk, preserve_index=False)
            if writer is None:
                target_schema = table.schema
                writer = pq.ParquetWriter(obs_clean_file, target_schema, compression="zstd")
            else:
                table = table.cast(target_schema)
            writer.write_table(table)

            del chunk, cleaned_chunk, table
            gc.collect()
        except Exception as e:
            logger.error(f"Error processing {f}: {e}")

    if writer is not None:
        writer.close()
    else:
        clean_cols = [c for c in CANONICAL_COLUMNS if c != "extras"]
        pd.DataFrame(columns=clean_cols).to_parquet(obs_clean_file, index=False, compression="zstd")

    final_report = pd.concat(reports, ignore_index=True) if reports else pd.DataFrame(columns=REPORT_COLUMNS)
    save_cleaning_report(final_report, data_dir=base_data_dir)

    rows_out = tot_rows_in
    valid_count = tot_valid
    flagged_count = tot_flagged

    logger.info(
        f"[STAGE: clean] Finished. rows_in={tot_rows_in} | rows_out={rows_out} "
        f"(valid={valid_count}, flagged={flagged_count}, run_id={actual_run_id})"
    )
    return {
        "stage": "clean",
        "rows_in": tot_rows_in,
        "rows_out": rows_out,
        "valid_count": valid_count,
        "flagged_count": flagged_count,
        "run_id": actual_run_id,
    }


def stage_cell_day(
    source: str | None = None,
    year: int | str | None = None,
    data_dir: Path | None = None,
    clear_tables: bool = True,
) -> dict[str, Any]:
    """Execute cell-day aggregation stage: valid obs_clean -> marts/cell_day_activity.parquet."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    obs_clean_file = base_data_dir / "staging" / "obs_clean.parquet"
    logger.info(f"[STAGE: cell_day] Starting (source={source}, year={year})")

    if not obs_clean_file.exists():
        logger.warning(f"obs_clean file not found at {obs_clean_file}")
        return {"stage": "cell_day", "rows_in": 0, "rows_out": 0}

    import pyarrow.parquet as pq

    req_cols = [
        "obs_id", "source_id", "sensor_family", "platform", "h3_cell",
        "local_date", "acq_date", "day_night", "confidence_class",
        "frp_mw", "is_valid", "static_masked",
    ]
    schema = pq.read_schema(obs_clean_file)
    avail_cols = [c for c in req_cols if c in schema.names]
    filters = [("is_valid", "==", True)] if "is_valid" in schema.names else None
    if source and "source_id" in schema.names:
        filters = (filters or []) + [("source_id", "==", source)]

    obs_clean = pd.read_parquet(obs_clean_file, columns=avail_cols, filters=filters)
    valid_mask = obs_clean["is_valid"] == True if "is_valid" in obs_clean.columns else pd.Series(True, index=obs_clean.index)
    if "static_masked" in obs_clean.columns:
        valid_mask &= (obs_clean["static_masked"] != True)
    if "qc_flags" in obs_clean.columns:
        valid_mask &= ~obs_clean["qc_flags"].astype(str).str.contains("possible_static_source", na=False)
    if year:
        date_c = "local_date" if "local_date" in obs_clean.columns else "acq_date"
        valid_mask &= obs_clean[date_c].astype(str).str.startswith(str(year))

    valid_df = obs_clean[valid_mask]
    rows_in = len(valid_df)

    if rows_in == 0:
        logger.info("[STAGE: cell_day] 0 valid rows to aggregate.")
        # Create empty mart if not existing or clearing
        cols = [
            "source_id", "sensor_family", "platform", "h3_cell",
            "date", "day_night", "n_detections", "n_high_conf",
            "frp_sum_mw", "frp_max_mw",
        ]
        empty_cell_day = pd.DataFrame(columns=cols)
        write_mart(empty_cell_day, "cell_day_activity", data_dir=base_data_dir)
        return {"stage": "cell_day", "rows_in": 0, "rows_out": 0}

    cell_day_df = aggregate_cell_day_activity(valid_df)

    # Handle single-source append only if clear_tables is False
    mart_path = base_data_dir / "marts" / "cell_day_activity.parquet"
    if not clear_tables and source and mart_path.exists():
        try:
            existing = pd.read_parquet(mart_path)
            if year:
                existing = existing[
                    ~((existing["source_id"] == source) & (existing["date"].astype(str).str.startswith(str(year))))
                ]
            else:
                existing = existing[existing["source_id"] != source]
            cell_day_df = pd.concat([existing, cell_day_df], ignore_index=True)
        except Exception:
            pass

    write_mart(cell_day_df, "cell_day_activity", data_dir=base_data_dir)
    rows_out = len(cell_day_df)
    logger.info(f"[STAGE: cell_day] Finished. rows_in={rows_in} | rows_out={rows_out}")
    return {"stage": "cell_day", "rows_in": rows_in, "rows_out": rows_out}


def stage_harmonize(
    method_id: str | None = None,
    data_dir: Path | None = None,
    data_version: str | None = None,
) -> dict[str, Any]:
    """Execute harmonization stage: fit calibration suite on clean SP data and apply to cell_day_activity.

    Generates:
        - data/marts/harmonized_cell_day.parquet
        - data/marts/calibration_models.parquet
    """
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    obs_clean_file = base_data_dir / "staging" / "obs_clean.parquet"
    cell_day_file = base_data_dir / "marts" / "cell_day_activity.parquet"
    harm_file = base_data_dir / "marts" / "harmonized_cell_day.parquet"

    logger.info(f"[STAGE: harmonize] Starting (method_id={method_id})")

    harm_cols = [
        "h3_cell", "acq_date", "day_night", "region_id", "harmonized_value",
        "harmonized_lower", "harmonized_upper", "modis_observed",
        "modis_terra_observed", "modis_aqua_observed", "viirs_observed",
        "viirs_platform", "platform_used", "interval_level", "method_id",
        "value_type", "is_provisional", "calibration_version", "data_version",
    ]

    if not cell_day_file.exists():
        logger.warning(f"cell_day_activity not found at {cell_day_file}")
        empty_harm = pd.DataFrame(columns=harm_cols)
        write_mart(empty_harm, "harmonized_cell_day", data_dir=base_data_dir)
        return {"stage": "harmonize", "rows_in": 0, "rows_out": 0, "cell_days_fit": 0, "mart": str(harm_file)}

    cell_day_df = pd.read_parquet(cell_day_file)
    rows_in = len(cell_day_df)

    if rows_in == 0:
        logger.info("[STAGE: harmonize] 0 cell-days to harmonize.")
        empty_harm = pd.DataFrame(columns=harm_cols)
        write_mart(empty_harm, "harmonized_cell_day", data_dir=base_data_dir)
        return {"stage": "harmonize", "rows_in": 0, "rows_out": 0, "cell_days_fit": 0, "mart": str(harm_file)}

    # Calibration dataset: prefer point-level obs_clean (SP only, no static sources)
    if obs_clean_file.exists():
        schema = pq.read_schema(obs_clean_file)
        cal_cols = [
            c for c in ["obs_id", "platform", "h3_cell", "local_date", "acq_date", "day_night", "processing_stream", "qc_flags", "is_valid"]
            if c in schema.names
        ]
        filters = []
        if "is_valid" in schema.names:
            filters.append(("is_valid", "==", True))
        if "processing_stream" in schema.names:
            filters.append(("processing_stream", "==", "SP"))
        cal_input = pd.read_parquet(
            obs_clean_file,
            columns=cal_cols,
            filters=filters if filters else None,
        )
    else:
        cal_input = cell_day_df

    # Fit calibration suite (Terra & Aqua separate models, joint model, bridging, bootstrap uncertainty)
    suite = fit_calibration_suite(cal_input, method_id=method_id)

    # Apply calibration models and output harmonized_cell_day and calibration_models marts
    harm_df = apply_calibration_to_cell_days(cell_day_df, suite, data_dir=base_data_dir, data_version=data_version)
    rows_out = len(harm_df)

    logger.info(
        f"[STAGE: harmonize] Finished. rows_in={rows_in} | rows_out={rows_out} | "
        f"cell_days_fit={suite.total_cell_days_fit}"
    )
    return {
        "stage": "harmonize",
        "rows_in": rows_in,
        "rows_out": rows_out,
        "cell_days_fit": suite.total_cell_days_fit,
        "mart": str(harm_file),
    }


def stage_monthly(data_dir: Path | None = None) -> dict[str, Any]:
    """Execute monthly summary stage: harmonized_cell_day -> marts/monthly_activity.parquet."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    harm_file = base_data_dir / "marts" / "harmonized_cell_day.parquet"
    monthly_file = base_data_dir / "marts" / "monthly_activity.parquet"

    rows_in = 0
    monthly_cols = [
        "region_id", "year_month", "value_type", "sensor_family",
        "value", "lower", "upper", "is_provisional", "is_partial", "data_version",
    ]

    if harm_file.exists():
        try:
            harm_df = pd.read_parquet(harm_file)
            rows_in = len(harm_df)
            if not harm_df.empty and "acq_date" in harm_df.columns:
                harm_df["year_month"] = pd.to_datetime(harm_df["acq_date"]).dt.strftime("%Y-%m")

                # Detect and remove spillover month (e.g. 2023-01 having <= 2 days at the tail of multi-year run)
                month_days = harm_df.groupby("year_month")["acq_date"].nunique()
                max_ym = harm_df["year_month"].max()
                days_in_max_ym = int(month_days.get(max_ym, 0))
                median_days = float(month_days.median())

                # If the trailing month has <= 2 days while earlier months have >= 20 days, drop it as spillover
                if len(month_days) > 1 and days_in_max_ym <= 2 and median_days >= 20:
                    harm_df = harm_df[harm_df["year_month"] != max_ym].copy()

                has_lower = "harmonized_lower" in harm_df.columns
                has_upper = "harmonized_upper" in harm_df.columns
                has_prov = "is_provisional" in harm_df.columns

                agg_dict: dict[str, Any] = {"value": ("harmonized_value", "sum")}
                if has_lower:
                    agg_dict["lower"] = ("harmonized_lower", "sum")
                if has_upper:
                    agg_dict["upper"] = ("harmonized_upper", "sum")
                if has_prov:
                    agg_dict["is_provisional"] = ("is_provisional", "any")

                grouped = harm_df.groupby(["region_id", "year_month"], as_index=False).agg(**agg_dict)
                grouped["value_type"] = "detections"
                grouped["sensor_family"] = "HARMONIZED"
                if not has_lower:
                    grouped["lower"] = grouped["value"] * 0.9
                if not has_upper:
                    grouped["upper"] = grouped["value"] * 1.1
                if not has_prov:
                    grouped["is_provisional"] = False

                grouped["is_partial"] = False
                grouped["data_version"] = "provisional"
                monthly_df = grouped[monthly_cols]
            else:
                monthly_df = pd.DataFrame(columns=monthly_cols)
        except Exception:
            monthly_df = pd.DataFrame(columns=monthly_cols)
    else:
        monthly_df = pd.DataFrame(columns=monthly_cols)

    write_mart(monthly_df, "monthly_activity", data_dir=base_data_dir)
    rows_out = len(monthly_df)
    logger.info(f"[STAGE: monthly] rows_in={rows_in} | rows_out={rows_out}")
    return {"stage": "monthly", "rows_in": rows_in, "rows_out": rows_out, "mart": str(monthly_file)}


# -----------------------------------------------------------------------------
# Full Pipeline Runner
# -----------------------------------------------------------------------------


def run_pipeline(
    stage: str = "all",
    source: str | None = None,
    year: int | str | None = None,
    sample: int | None = None,
    sample_mode: str = "first",
    method_id: str | None = None,
    data_dir: Path | None = None,
    data_version: str | None = None,
    run_id: str | None = None,
    clear_tables: bool = True,
) -> dict[str, Any]:
    """Execute specified pipeline stage(s), synchronize DuckDB, and write manifest.

    Args:
        stage: 'all', 'ingest', 'clean', 'cell_day', 'harmonize', or 'monthly'.
        source: Optional source_id filter (e.g. 'viirs_noaa20').
        year: Optional year filter (e.g. 2023).
        sample: Optional row limit per file for fast testing.
        sample_mode: 'first' (first N rows) or 'spread' (every k-th row across file).
        method_id: Optional calibration method override (e.g. 'stratified_ratio', 'global_ratio').
        data_dir: Target data directory (default: settings.data_dir).
        data_version: Optional explicit data_version string.
        run_id: Optional unique identifier for this run.
        clear_tables: Whether staging and marts tables are cleared/isolated for this run (default: True).

    Returns:
        Summary dict containing stage metrics, DuckDB sync status, and manifest.
    """
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    base_data_dir.mkdir(parents=True, exist_ok=True)

    stage = stage.lower().strip()
    actual_run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    logger.info(
        f"=== Running TerraFlare Pipeline (stage={stage}, source={source}, year={year}, sample={sample}, mode={sample_mode}, run_id={actual_run_id}) ==="
    )

    results: dict[str, Any] = {"requested_stage": stage, "run_id": actual_run_id, "stages": {}}

    if stage in ("all", "ingest"):
        results["stages"]["ingest"] = stage_ingest(
            source=source,
            year=year,
            sample=sample,
            sample_mode=sample_mode,
            data_dir=base_data_dir,
        )

    if stage in ("all", "clean"):
        results["stages"]["clean"] = stage_clean(
            source=source,
            year=year,
            sample=sample,
            data_dir=base_data_dir,
            run_id=actual_run_id,
            clear_tables=clear_tables,
        )

    if stage in ("all", "cell_day"):
        results["stages"]["cell_day"] = stage_cell_day(
            source=source,
            year=year,
            data_dir=base_data_dir,
            clear_tables=clear_tables,
        )

    if stage in ("all", "harmonize"):
        results["stages"]["harmonize"] = stage_harmonize(
            method_id=method_id, data_dir=base_data_dir, data_version=data_version
        )

    if stage in ("all", "monthly"):
        results["stages"]["monthly"] = stage_monthly(data_dir=base_data_dir)

    # Synchronize DuckDB views
    try:
        con = sync_duckdb_views(data_dir=base_data_dir)
        con.close()
        results["duckdb_synced"] = True
    except Exception as e:
        logger.error(f"Failed to synchronize DuckDB views: {e}")
        results["duckdb_synced"] = False

    # Generate and write manifest
    manifest = write_manifest(data_dir=base_data_dir, data_version=data_version)
    results["manifest"] = manifest

    logger.info("=== TerraFlare Pipeline Completed Successfully ===")
    return results
