import duckdb
import numpy as np

con = duckdb.connect('data/terraflare.duckdb', read_only=True)

modes = [
    ('Double Counted (Old)', 'harmonized_value'),
    ('Double Count Removed (Clean)', "CASE WHEN acq_date >= '2012-01-20' AND viirs_platform = 'none' THEN 0.0 ELSE harmonized_value END")
]

for mode_name, harm_col in modes:
    df = con.execute(f"""
        SELECT 
            EXTRACT(year FROM acq_date)::INTEGER AS yr,
            ROUND(SUM({harm_col}), 2) AS nov_val
        FROM harmonized_cell_day
        WHERE EXTRACT(month FROM acq_date) = 11 AND EXTRACT(day FROM acq_date) <= 9
        GROUP BY yr
        ORDER BY yr
    """).df()
    
    current_val = float(df.loc[df['yr'] == 2026, 'nov_val'].values[0])
    base_vals = df.loc[(df['yr'] >= 2012) & (df['yr'] <= 2025), 'nov_val'].values.astype(float)
    med = float(np.median(base_vals))
    ratio = current_val / med
    print(f"=== {mode_name} ===")
    print(f"Current 2026 (Nov 1-9): {current_val:,.1f}")
    print(f"Baseline Median (2012-2025): {med:,.1f}")
    print(f"Current vs Median Ratio: {ratio:.4f}x ({ratio*100:.2f}%)")
    print(f"Baseline values: {[round(x, 1) for x in sorted(base_vals)]}")
    print()

