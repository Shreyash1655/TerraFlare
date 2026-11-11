"""Tests for application settings and validators."""

from __future__ import annotations

import json
from app.settings import Settings


def test_cors_origins_from_comma_separated_string():
    s = Settings(CORS_ORIGINS="http://localhost:3000, http://localhost:5173")
    assert s.cors_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_cors_origins_from_json_array_string():
    json_val = json.dumps(["http://localhost:3000", "http://localhost:5173"])
    s = Settings(CORS_ORIGINS=json_val)
    assert s.cors_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_cors_origins_from_single_url():
    s = Settings(CORS_ORIGINS="http://localhost:5173")
    assert s.cors_origins == ["http://localhost:5173"]


def test_cors_origins_from_list():
    s = Settings(CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"])
    assert s.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]

