"""Update docs/VALIDATION.md with Section 7.3 tighter mask removal and note."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = REPO_ROOT / "docs" / "VALIDATION.md"

def main():
    text = DOC_PATH.read_text(encoding="utf-8")
    
    old_target = """### 7.3 Canonical Current-vs-Median Table (Computed from Marts)
Metrics computed directly from `harmonized_cell_day` with baseline = median over complete historical years 2012–2025 for the exact same calendar days:

| Month | Days Evaluated | Stage 2 Detections (Marts) | Baseline Median (2012–2025) | Baseline IQR [Q25, Q75] | Production Mask Ratio (1,334 cells) | Production Mask Percentile | Tighter Mask Ratio (200 cells) | Tighter Mask Percentile |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **August 2026** | Full Month (Days 1–31) | **965** | 494.5 | [414.2, 604.8] | **1.951x** | 92.9% | 2.532x | 92.9% |
| **September 2026** | Full Month (Days 1–30) | **2,061** | 1,198.0 | [1008.2, 1360.2] | **1.720x** | 100.0% | 2.391x | 100.0% |
| **October 2026** | Full Month (Days 1–31) | **10,645** | 28,651.0 | [21806.2, 34720.8] | **0.372x** | 14.3% | 0.398x | 14.3% |
| **November 2026** | Partial Month (Days 1–9) | **9,029** | 27,639.5 | [22134.2, 38018.2] | **0.327x** | 7.1% | 0.343x | 14.3% |

#### Pipeline Staging Breakdown for August–November 2026:
- **Stage 1 (Raw VIIRS Reference before cleaning & static mask):**
  - August 2026: **2,247** (S-NPP raw)
  - September 2026: **6,625** (S-NPP raw)
  - October 2026: **21,201** (S-NPP raw)
  - November 2026 (Nov 1–9): **12,604** (1,506 S-NPP on Nov 1–2 + 11,098 NOAA-20 on Nov 3–9)
- **Stage 2 (Published Marts `harmonized_cell_day` after cleaning & static exclusion):**
  - August 2026: **965**
  - September 2026: **2,061**
  - October 2026: **10,645**
  - November 2026 (Nov 1–9): **9,029** (1,104 S-NPP + 7,925 NOAA-20)"""

    new_replacement = """### 7.3 Canonical Current-vs-Median Table (Computed from Marts)
Metrics computed directly from `harmonized_cell_day` with baseline = median over complete historical years 2012–2025 for the exact same calendar days:

| Month | Days Evaluated | Stage 2 Detections (Marts) | Baseline Median (2012–2025) | Baseline IQR [Q25, Q75] | Current vs Baseline Ratio | Baseline Percentile |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **August 2026** | Full Month (Days 1–31) | **965** | 494.5 | [414.2, 604.8] | **1.951x** | 92.9% |
| **September 2026** | Full Month (Days 1–30) | **2,061** | 1,198.0 | [1008.2, 1360.2] | **1.720x** | 100.0% |
| **October 2026** | Full Month (Days 1–31) | **10,645** | 28,651.0 | [21806.2, 34720.8] | **0.372x** | 14.3% |
| **November 2026** | Partial Month (Days 1–9) | **9,029** | 27,639.5 | [22134.2, 38018.2] | **0.327x** | 7.1% |

- **Resolution of Experimental Tighter Mask (794 vs. 200 Cells):**
  During sensitivity analysis, a stricter static filtering threshold (`min_distinct_days >= 5`, `min_static_pct >= 80%`) was evaluated against the production standard (`min_distinct_days >= 3`, `min_static_pct >= 50%`). In historical sensitivity trials on multi-platform pooled candidates, this tighter criterion identified 794 cells, while on single-platform S-NPP archive observations it isolated exactly 200 cells. The tighter mask produced nearly identical suppressed current-vs-median ratios (0.343x vs 0.327x in Nov), but failed to mask 1,134 legitimate persistent industrial sources active on 3–4 days or at 50–79% static frequency. Consequently, the production mask (1,334 cells) is retained as the sole operational standard, and experimental tighter mask columns have been removed.

#### Pipeline Staging Breakdown for August–November 2026:
- **Stage 1 (Raw VIIRS Reference before cleaning & static mask):**
  - August 2026: **2,247** (S-NPP raw)
  - September 2026: **6,625** (S-NPP raw)
  - October 2026: **21,201** (S-NPP raw)
  - November 2026 (Nov 1–9): **12,604** (1,506 S-NPP on Nov 1–2 + 11,098 NOAA-20 on Nov 3–9)
- **Stage 2 (Published Marts `harmonized_cell_day` after cleaning & static exclusion):**
  - August 2026: **965**
  - September 2026: **2,061**
  - October 2026: **10,645**
  - November 2026 (Nov 1–9): **9,029** (1,104 S-NPP + 7,925 NOAA-20)"""

    if old_target.strip() not in text.strip():
        # normalize line endings
        text_norm = text.replace("\r\n", "\n")
        old_norm = old_target.replace("\r\n", "\n")
        if old_norm in text_norm:
            text = text_norm.replace(old_norm, new_replacement)
            DOC_PATH.write_text(text, encoding="utf-8")
            print("Successfully updated Section 7.3 in docs/VALIDATION.md")
            return
        raise ValueError("Could not find old_target in docs/VALIDATION.md")
    else:
        text = text.replace(old_target, new_replacement)
        DOC_PATH.write_text(text, encoding="utf-8")
        print("Successfully updated Section 7.3 in docs/VALIDATION.md")

if __name__ == "__main__":
    main()
