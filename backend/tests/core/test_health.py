"""Tests for GET /api/v1/health."""

from __future__ import annotations

import os
import sys

import pytest

# Force fixture mode so the test never tries to open real parquet files.
os.environ.setdefault("TERRAFLARE_DATA_MODE", "fixture")

from app.api.routes_core.health import health
from app.main import app

HEALTH_URL = "/api/v1/health"


def _get_health_body() -> dict:
    if sys.version_info >= (3, 14):
        # Under Python 3.14 dev, call route function directly to avoid Starlette/anyio deadlock
        res = health()
        data = res["data"] if isinstance(res, dict) else res
        return data.model_dump() if hasattr(data, "model_dump") else data
    else:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        res = client.get(HEALTH_URL).json()
        return res["data"] if "data" in res else res


def test_health_returns_200():
    if sys.version_info >= (3, 14):
        res = health()
        data = res["data"] if isinstance(res, dict) else res
        assert data.status == "ok"
    else:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.get(HEALTH_URL)
        assert r.status_code == 200
        res = r.json()
        data = res["data"] if "data" in res else res
        assert data["status"] == "ok"


def test_health_body_shape():
    body = _get_health_body()
    assert body["status"] == "ok"
    assert "service" in body
    assert "data_mode" in body
    assert "is_synthetic" in body
    # data_version may be None if manifest.json is absent – that is acceptable
    assert "data_version" in body


def test_health_is_synthetic_when_fixture_mode():
    """When data_mode=fixture, is_synthetic must be True."""
    body = _get_health_body()
    assert body["data_mode"] == "fixture"
    assert body["is_synthetic"] is True


def test_root_endpoint():
    """Root endpoint should return doc links."""
    from app.main import root
    res = root()
    assert "docs" in res


