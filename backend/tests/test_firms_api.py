import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
KEYS = {"mode", "data_label", "note", "count", "items"}
CELL = {"h3_cell", "lat", "lon", "source_dataset", "sensor_family", "platform_group",
        "observation_count", "frp_sum", "frp_mean", "frp_max", "high_conf_count", "product_type"}
META = {"dataset", "sensor", "platform", "resolution", "product_type", "n_raw", "n_final", "label"}
SHAPES = {"/api/v1/advanced/firms/datasets": META, "/api/v1/advanced/firms/h3": CELL,
          "/api/v1/advanced/firms/heatmap/daily": CELL | {"acq_day"}}


def _expected_label_token(items):
    types = {i["product_type"] for i in items}
    if types == {"NRT"}:
        return "NRT"
    if types == {"SP"}:
        return "Standard processing"
    return "Mixed"


@pytest.mark.parametrize("mode", ["real", "synthetic"])
@pytest.mark.parametrize("path", list(SHAPES))
def test_contract(path, mode, monkeypatch):
    monkeypatch.setenv("FIRMS_MODE", mode)
    r = client.get(path)
    assert r.status_code == 200
    j = r.json()
    assert KEYS <= j.keys() and j["mode"] == mode
    assert j["count"] == len(j["items"]) > 0
    assert SHAPES[path] <= j["items"][0].keys()
    assert all(i["product_type"] in {"NRT", "SP", "MIXED"} for i in j["items"])
    # Label must follow the product_type of the returned rows, never be hardcoded.
    assert _expected_label_token(j["items"]).lower() in j["data_label"].lower()


def test_real_filters(monkeypatch):
    monkeypatch.setenv("FIRMS_MODE", "real")
    ds = client.get("/api/v1/advanced/firms/datasets").json()["items"]
    name = next(d["dataset"] for d in ds if d["dataset"].startswith("MODIS"))
    j = client.get("/api/v1/advanced/firms/heatmap/daily",
                   params={"date": "2026-11-12", "dataset": name}).json()
    assert j["mode"] == "real" and j["count"] > 0
    assert {i["acq_day"] for i in j["items"]} == {"2026-11-12"}