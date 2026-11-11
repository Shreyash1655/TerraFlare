"""Backward-compatibility shim – re-exports Settings and settings from app.settings.

New code should import directly from app.settings.
Existing advanced-API code that imports from app.core.config continues to work.
"""

from __future__ import annotations

from app.settings import Settings, settings  # noqa: F401

__all__ = ["Settings", "settings"]
