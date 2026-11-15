"""Cleaning report generation and storage for TerraFlare data pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.cleaning.normalize import normalize_canonical_dataframe
from app.core.cleaning.rules import CONFIDENCE_LEVELS, apply_cleaning_rules
from app.core.cleaning.static_mask import (
    apply_static_source_mask,
    build_static_source_mask,
    get_static_mask_config,
    load_static_mask,
    save_static_mask,
)
from app.settings import settings
from app.shared.config_loader import get_harmonization_config

REPORT_COLUMNS = ["run_id", "rule_id", "source_id", "rows_flagged", "rows_dropped"]


def build_cleaning_report(
    records: list[dict[str, Any]],
    source_id: str = "unknown",
    run_id: str = "default",
) -> pd.DataFrame:
    """Build a standard cleaning report DataFrame from per-rule count dicts.

    Columns:
        run_id, rule_id, source_id, rows_flagged, rows_dropped
    """
    rows = []
    for r in records:
        rows.append({
            "run_id": str(r.get("run_id", run_id)),
            "rule_id": str(r.get("rule_id", "unknown")),
            "source_id": str(r.get("source_id", source_id)),
            "rows_flagged": int(r.get("rows_flagged", 0)),
            "rows_dropped": int(r.get("rows_dropped", 0)),
        })
    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    return df


def save_cleaning_report(
    report_df: pd.DataFrame,
    data_dir: Path | None = None,
) -> Path:
    """Write cleaning_report.parquet in data/staging/ reflecting this run."""
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    staging_dir = base_data_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    out_path = staging_dir / "cleaning_report.parquet"
    report_df.to_parquet(out_path, index=False)
    return out_path


def format_cleaning_report(report_df: pd.DataFrame) -> str:
    """Return a formatted string summary of the cleaning report."""
    if report_df.empty:
        return "No cleaning records."

    has_run_id = "run_id" in report_df.columns
    header = (
        f"{'RUN ID':<18} | {'RULE ID':<25} | {'SOURCE':<15} | {'FLAGGED':<10} | {'DROPPED':<10}"
        if has_run_id
        else f"{'RULE ID':<25} | {'SOURCE':<15} | {'FLAGGED':<10} | {'DROPPED':<10}"
    )
    sep = "-" * len(header)
    lines = [sep, header, sep]
    for _, row in report_df.iterrows():
        if has_run_id:
            lines.append(
                f"{str(row.get('run_id', '')):<18} | {row['rule_id']:<25} | {row['source_id']:<15} | {row['rows_flagged']:<10} | {row['rows_dropped']:<10}"
            )
        else:
            lines.append(
                f"{row['rule_id']:<25} | {row['source_id']:<15} | {row['rows_flagged']:<10} | {row['rows_dropped']:<10}"
            )
    lines.append(sep)
    total_flagged = report_df["rows_flagged"].sum()
    total_dropped = report_df["rows_dropped"].sum()
    lines.append(f"TOTAL FLAGGED: {total_flagged} | TOTAL DROPPED: {total_dropped}")
    return "\n".join(lines)


def print_cleaning_report(report_df: pd.DataFrame) -> None:
    """Print the cleaning report table to stdout."""
    print(format_cleaning_report(report_df))


def clean_observations(
    df: pd.DataFrame,
    source_id: str | None = None,
    data_dir: Path | None = None,
    write_report: bool = True,
    min_confidence_class: str | None = None,
    allowed_fire_types: Any = None,
    run_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute normalisation and all cleaning rules on canonical observations.

    Invalid rows are marked with is_valid=False and qc_flags.
    Rows are NOT deleted – obs_clean keeps all rows.

    Returns:
        (obs_clean_df, cleaning_report_df)
    """
    actual_run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    sid = source_id or (df["source_id"].iloc[0] if not df.empty and "source_id" in df.columns else "all")

    # 1. Normalise confidence and local_date
    norm_df = normalize_canonical_dataframe(df)

    # 2. Apply cleaning rules (including duplicate_across_streams)
    cleaned_df, rule_records = apply_cleaning_rules(
        norm_df,
        min_confidence_class=min_confidence_class,
        allowed_fire_types=allowed_fire_types,
    )

    # Count consistency assertions (Task 7c):
    # Each rule's rows_flagged cannot exceed the rows its condition can match
    # 1. fire_type_filter <= rows with fire_type not 0
    if "fire_type" in df.columns:
        ft_non_zero = (
            df["fire_type"].notna()
            & (df["fire_type"] != "")
            & (df["fire_type"] != "None")
            & (~df["fire_type"].astype(str).str.strip().str.replace(".0", "", regex=False).isin(["0", "vegetation", "presumed vegetation fire"]))
        )
        max_possible_ft = int(ft_non_zero.sum())
        ft_rec = next((r for r in rule_records if r["rule_id"] == "fire_type_filter"), None)
        if ft_rec:
            assert ft_rec["rows_flagged"] <= max_possible_ft, (
                f"Count consistency error: fire_type_filter flagged {ft_rec['rows_flagged']} rows, "
                f"exceeding max possible non-0 fire_type rows ({max_possible_ft})."
            )

    # 2. confidence_filter <= rows below minimum confidence class
    if "confidence_class" in cleaned_df.columns:
        min_cls = min_confidence_class or get_harmonization_config().get("min_confidence_class", "nominal")
        min_lvl = CONFIDENCE_LEVELS.get(min_cls.lower(), 2)
        classes = cleaned_df["confidence_class"].fillna("unknown").astype(str).str.lower()
        levels = classes.map(CONFIDENCE_LEVELS).fillna(0)
        max_possible_conf = int((levels < min_lvl).sum())
        conf_rec = next((r for r in rule_records if r["rule_id"] == "confidence_filter"), None)
        if conf_rec:
            assert conf_rec["rows_flagged"] <= max_possible_conf, (
                f"Count consistency error: confidence_filter flagged {conf_rec['rows_flagged']} rows, "
                f"exceeding max possible rows below {min_cls} ({max_possible_conf})."
            )

    # 3. Static source mask from archive files on fine H3 grid (resolution 8)
    base_data_dir = Path(data_dir) if data_dir else settings.data_dir
    mask_cfg = get_static_mask_config()
    res8 = mask_cfg["h3_resolution"]
    min_days = mask_cfg["min_distinct_days"]
    min_pct = mask_cfg.get("min_static_pct", 50.0)
    static_types = mask_cfg["static_types"]

    is_sp = (
        cleaned_df["processing_stream"].astype(str).isin(["SP", "sp"])
        if "processing_stream" in cleaned_df.columns
        else pd.Series(True, index=cleaned_df.index)
    )
    archive_sub = cleaned_df[is_sp]
    new_mask = build_static_source_mask(
        archive_sub,
        h3_resolution=res8,
        min_distinct_days=min_days,
        min_static_pct=min_pct,
        static_types=static_types,
    )
    if new_mask:
        save_static_mask(new_mask, base_data_dir)
        active_mask = new_mask
    else:
        active_mask = load_static_mask(base_data_dir)

    if active_mask:
        cleaned_df, nrt_static_flagged, archive_in_mask = apply_static_source_mask(
            cleaned_df, active_mask, h3_resolution=res8
        )
        rule_records.append({
            "rule_id": "possible_static_source",
            "source_id": sid,
            "rows_flagged": nrt_static_flagged,
            "rows_dropped": 0,
        })

    # 4. Build cleaning report with run_id
    report_df = build_cleaning_report(rule_records, source_id=sid, run_id=actual_run_id)

    # 5. Save report
    if write_report:
        save_cleaning_report(report_df, data_dir=data_dir)

    return cleaned_df, report_df

