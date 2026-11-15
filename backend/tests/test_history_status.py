import pandas as pd
from app.services.history_service import build_history_status


def test_31_days_is_insufficient():
    df = pd.DataFrame({"acq_date": pd.date_range("2026-10-14", periods=31)})
    r = build_history_status(df, "firms_nrt", False)
    assert r["available_days"] == 31
    assert all(not m["sufficient"] for m in r["modules"].values())
    assert "firms_nrt" in r["modules"]["anomaly"]["message"]


def test_empty_is_insufficient_not_faked():
    r = build_history_status(None, "firms_nrt", False)
    assert r["available_days"] == 0 and r["date_range"] == [None, None]


def test_three_years_is_sufficient_for_season_shift():
    df = pd.DataFrame({"acq_date": pd.date_range("2023-01-01", "2026-01-01")})
    assert build_history_status(df, "x", False)["modules"]["season-shift"]["sufficient"]