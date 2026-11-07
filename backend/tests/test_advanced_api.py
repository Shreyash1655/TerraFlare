import os

os.environ["TERRAFLARE_DATA_MODE"] = "fixture"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
BASE = "/api/v1/advanced"


def get(path, **params):
    r = client.get(f"{BASE}{path}", params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meta"]["is_synthetic"] is True
    return body["data"]


def test_health():
    assert client.get(f"{BASE}/health").json()["is_synthetic"] is True


def test_season_shift_finds_earlier_onset():
    d = get("/season-shift")
    assert len(d["years"]) == 11
    assert d["comparison"]["onset_shift_days"]["estimate"] < 0   # planted: season drifts earlier
    assert d["trend"]["onset_slope_days_per_year"] < 0


def test_fire_memory_classes():
    d = get("/fire-memory/cells", limit=5000)
    assert d["class_counts"].get("declining", 0) > 0
    assert d["class_counts"].get("emerging", 0) > 0
    assert d["class_counts"].get("persistent", 0) > 0
    cell = d["cells"][0]["h3_cell"]
    t = get(f"/fire-memory/cells/{cell}/timeline")
    assert len(t["annual"]) == 11
    only = get("/fire-memory/cells", **{"class": "declining"})
    assert {c["memory_class"] for c in only["cells"]} == {"declining"}


def test_anomaly_flags_planted_summer_2023():
    d = get("/anomalies", start="2023-05-01", end="2023-09-30")
    top = max(d["periods"], key=lambda p: p["robust_z"] or -99)
    assert top["period_start"] <= "2023-07-09" and top["period_end"] >= "2023-06-19"
    assert top["is_anomalous"]
    e = get("/anomalies/explain", start="2023-06-19", end="2023-07-09")
    assert e["top_dates"] and e["top_cells"] and "does not state a cause" in e["explanation"]


def test_events():
    d = get("/events", start="2023-06-15", end="2023-07-15")
    assert d["events"] and "not verified wildfires" in d["label"]
    ev = d["events"][0]["event_id"]
    detail = get(f"/events/{ev}")
    assert detail["daily"]


def test_exposure():
    d = get("/exposure", start="2023-06-15", end="2023-07-15", buffer_km=5)
    assert d["layers"][0]["available"] and d["layers"][0]["count"] > 0
    d = get("/exposure", start="2023-06-15", end="2023-07-15", layers="roads")
    assert d["layers"][0]["available"] is False and d["layers"][0]["count"] is None


def test_quality_detects_planted_viirs_gap():
    d = get("/quality", start="2022-01-01", end="2022-12-31")
    gaps = [g for g in d["availability"] if g["sensor_family"] == "VIIRS"]
    assert any(g["gap_start"] <= "2022-06-24" and g["gap_end"] >= "2022-06-24" for g in gaps)
    assert d["confidence_distribution"] and d["confidence_normalised"]
    p = get("/quality/provenance")
    assert len(p["sources"]) == 2


def test_errors_use_common_shape():
    r = client.get(f"{BASE}/anomalies", params={"start": "2023-02-01", "end": "2023-01-01"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_date_range"
    r = client.get(f"{BASE}/events/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "event_not_found"