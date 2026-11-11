"""Backward-compatibility shim – re-exports from app.shared.errors.

New code should import directly from app.shared.errors.
Existing advanced-API code that imports from app.utils.errors continues to work.
"""

from __future__ import annotations

from app.shared.errors import TerraFlareError, register_error_handlers  # noqa: F401

__all__ = ["TerraFlareError", "register_error_handlers"]
