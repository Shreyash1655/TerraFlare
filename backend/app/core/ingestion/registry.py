"""Adapter registry – maps adapter_name strings to adapter classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.ingestion.base import BaseAdapter

_REGISTRY: dict[str, type["BaseAdapter"]] = {}


def register(cls: type["BaseAdapter"], name: str | None = None) -> type["BaseAdapter"]:
    """Class decorator or function that registers an adapter in the registry."""
    key = name or getattr(cls, "adapter_name", getattr(cls, "source_id", cls.__name__.lower()))
    _REGISTRY[key] = cls
    return cls


def get(adapter_name: str) -> type["BaseAdapter"]:
    """Return the adapter class for the given adapter name, raising KeyError if unknown."""
    if adapter_name not in _REGISTRY:
        # Try loading known adapters
        if adapter_name == "firms_csv":
            from app.core.ingestion.adapters.firms_csv import FirmsCSVAdapter
            register(FirmsCSVAdapter, "firms_csv")
            return FirmsCSVAdapter
        raise KeyError(
            f"No adapter registered for name='{adapter_name}'. "
            f"Registered adapters: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[adapter_name]


def list_registered() -> list[str]:
    """Return all registered adapter names."""
    # Ensure standard adapters are included
    if "firms_csv" not in _REGISTRY:
        from app.core.ingestion.adapters.firms_csv import FirmsCSVAdapter
        register(FirmsCSVAdapter, "firms_csv")
    return list(_REGISTRY.keys())


# Register standard adapters at module import
from app.core.ingestion.adapters.firms_csv import FirmsCSVAdapter
register(FirmsCSVAdapter, "firms_csv")
