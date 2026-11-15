import numpy as np
import pandas as pd
import pytest
from app.services import short_window_service as svc
from app.utils.errors import TerraFlareError


def _obs(days, per_day=1200, sensor="VIIRS", platform="NOAA-20", spike_day=None):
    rows = []
    for i, d in enumerate(pd.date_range("2026-10-15", periods=days)):
        n = (per_day + (i % 5) * 20) * (5 if spike_day == i else 1)
        rows.append(pd.DataFrame({"local_date": d, "sensor_family": sensor, "platform": platform,
                                  "is_valid": True, "h3_cell": [f"c{j % 50}" for j in range(n)]}))
    return pd.concat(rows, ignore_index=True)

def test_under_14_days_gives_no_scores():
    r = svc.anomalies(_obs(10), "viirs")
    assert r["days"] == [] and any("Needs 14" in w for w in r["warnings"])


def test_spike_is_flagged():
    r = svc.anomalies(_obs(30, spike_day=20), "viirs")
    assert any(x["flagged"] for x in r["days"] if x["date"] == "2026-11-04")


def test_low_coverage_days_excluded_not_zero():
    o = _obs(30, per_day=1200)
    o = o[~((o["local_date"] == "2026-10-20") & (o.index % 2 == 0))]
    o = o[o["local_date"] != "2026-10-21"]
    r = svc.anomalies(o, "viirs")
    assert r["usable_days"] <= 29 and all(x["date"] != "2026-10-21" for x in r["days"])


def test_wrong_platform_is_not_used():
    with pytest.raises(TerraFlareError):
        svc.anomalies(_obs(30, platform="NOAA-21"), "viirs")


def test_persistence_share():
    r = svc.persistence(_obs(30), "viirs")
    assert r["covered_days"] == 30 and r["cells"][0]["share"] == 1.0
    assert r["method"] == "short_window"

def test_zero_spread_gives_null_score_not_fabricated():
    r = svc.anomalies(_obs(30, spike_day=20).assign(), "viirs")
    flat = svc.anomalies(pd.concat([
        pd.DataFrame({"local_date": d, "sensor_family": "VIIRS", "platform": "NOAA-20",
                      "is_valid": True, "h3_cell": [f"c{j % 50}" for j in range(1200)]})
        for d in pd.date_range("2026-10-15", periods=20)], ignore_index=True), "viirs")
    assert all(x["robust_z"] is None and x["flagged"] is False for x in flat["days"])

def test_persistence_tiebreak_and_counts():
    o = _obs(30)
    extra = pd.DataFrame({"local_date": pd.date_range("2026-10-15", periods=30),
                          "sensor_family": "VIIRS", "platform": "NOAA-20",
                          "is_valid": True, "h3_cell": "heavy"})
    extra = pd.concat([extra] * 200, ignore_index=True)
    r = svc.persistence(pd.concat([o, extra], ignore_index=True), "viirs")
    assert r["cells"][0]["h3_cell"] == "heavy"
    assert r["cells"][0]["detections"] == 6000
    assert r["cells_full"] >= 1 and r["n_cells"] >= r["cells_full"]