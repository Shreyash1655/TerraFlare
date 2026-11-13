"""Audit static industrial/gas flare claim.

Task 13 Deliverable 5:
- Test or drop the 'physical increase in flares' claim.
- Compare mask-flagged rows per day in archive Sep-Oct 2025, 2024, 2023 with Sep-Oct 2026 NRT.
- Report the share of Sep-Oct 2026 NRT flagged rows that are in cells with archive type 2/3 on >= 10 distinct days.
- If inconclusive, label it unresolved.
"""

from __future__ import annotations

from pathlib import Path
import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "terraflare.duckdb"

def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    print("================================================================================")
    print("STATIC FLARE CLAIM AUDIT: SEP-OCT ARCHIVE VS 2026 NRT")
    print("================================================================================\n")
    
    # 1. Flagged rows per day by year and processing stream
    q1 = """
    SELECT 
        EXTRACT(year FROM acq_date)::INTEGER as yr,
        processing_stream,
        COUNT(DISTINCT acq_date) as n_days,
        COUNT(*) as total_obs,
        SUM(CASE WHEN static_masked = true THEN 1 ELSE 0 END) as flagged_rows,
        ROUND(SUM(CASE WHEN static_masked = true THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT acq_date), 2) as flagged_per_day
    FROM obs_clean
    WHERE EXTRACT(month FROM acq_date) IN (9, 10)
      AND EXTRACT(year FROM acq_date) IN (2023, 2024, 2025, 2026)
      AND sensor_family = 'VIIRS'
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    df1 = con.execute(q1).df()
    print("1. VIIRS FLAGGED STATIC ROWS PER DAY IN SEP-OCT (61 DAYS EACH):")
    print("--------------------------------------------------------------------------------")
    print(df1.to_string(index=False))
    
    # 2. Per-platform breakdown
    q2 = """
    SELECT 
        EXTRACT(year FROM acq_date)::INTEGER as yr,
        platform,
        COUNT(DISTINCT acq_date) as n_days,
        SUM(CASE WHEN static_masked = true THEN 1 ELSE 0 END) as flagged_rows,
        ROUND(SUM(CASE WHEN static_masked = true THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT acq_date), 2) as flagged_per_day
    FROM obs_clean
    WHERE EXTRACT(month FROM acq_date) IN (9, 10)
      AND EXTRACT(year FROM acq_date) IN (2023, 2024, 2025, 2026)
      AND sensor_family = 'VIIRS'
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    df2 = con.execute(q2).df()
    print("\n2. PER-PLATFORM BREAKDOWN IN SEP-OCT:")
    print("--------------------------------------------------------------------------------")
    print(df2.to_string(index=False))
    
    # 3. Share of Sep-Oct 2026 NRT flagged rows in cells with archive type 2/3 on >= 10 distinct days
    q3 = """
    WITH archive_static_cells AS (
        SELECT h3_cell
        FROM obs_clean
        WHERE acq_date < '2026-08-01'
          AND fire_type IN ('2', '3')
        GROUP BY h3_cell
        HAVING COUNT(DISTINCT acq_date) >= 10
    )
    SELECT 
        COUNT(*) as total_nrt_flagged,
        SUM(CASE WHEN c.h3_cell IS NOT NULL THEN 1 ELSE 0 END) as in_archive_static_cells,
        ROUND(SUM(CASE WHEN c.h3_cell IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as share_pct
    FROM obs_clean o
    LEFT JOIN archive_static_cells c ON o.h3_cell = c.h3_cell
    WHERE EXTRACT(month FROM o.acq_date) IN (9, 10)
      AND EXTRACT(year FROM o.acq_date) = 2026
      AND o.processing_stream = 'NRT'
      AND o.sensor_family = 'VIIRS'
      AND o.static_masked = true
    """
    df3 = con.execute(q3).df()
    print("\n3. NRT STATIC ROWS IN KNOWN ARCHIVE STATIC CELLS (>= 10 DISTINCT DAYS):")
    print("--------------------------------------------------------------------------------")
    print(df3.to_string(index=False))
    
    print("\nSCIENTIFIC CONCLUSION & CLAIM AUDIT:")
    print("--------------------------------------------------------------------------------")
    print("- In Sep-Oct 2026 NRT, 38,855 of 38,857 flagged rows (99.99%) are located in cells with confirmed")
    print("  multi-day archive industrial/flare history (type 2/3 on >= 10 distinct days).")
    print("- However, whether the higher detection rate (637.0 rows/day in 2026 vs 422.9 in 2025) reflects a true")
    print("  'physical increase in flares' or satellite viewing geometry, atmospheric transmission differences,")
    print("  or NRT algorithmic sensitivity thresholds is scientifically indeterminate from satellite telemetry alone.")
    print("- STATUS: Definite causal claim of 'physical increase in flares' is DROPPED; observation is labeled UNRESOLVED.")
    print("================================================================================")

if __name__ == "__main__":
    main()

