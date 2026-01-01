"""
Allowlists and denylists for dynamic tool generation from xarray-like objects.

This module provides curated lists of methods that are safe to expose as MCP tools.
The goal is to prevent memory leaks (by forbidding eager loading of large datasets)
and ensuring consistent behavior across different tool implementations.
"""

from typing import Any

XARRAY_ALLOWLIST: dict[str, dict[str, Any]] = {
    "rename": {"signature": "(mapping: dict[str, str])", "category": "axis"},
    "squeeze": {"signature": "(dim: str | None = None)", "category": "axis"},
    "expand_dims": {"signature": "(dim: str | dict, axis: int | None = None)", "category": "axis"},
    "transpose": {"signature": "(*dims: str)", "category": "axis"},
    "isel": {"signature": "(**indexers: int | slice)", "category": "selection"},
    "pad": {"signature": "(pad_width: dict[str, tuple[int, int]])", "category": "transform"},
    "sum": {"signature": "(dim: str | list[str] | None = None)", "category": "reduction"},
    "max": {"signature": "(dim: str | list[str] | None = None)", "category": "reduction"},
    "mean": {"signature": "(dim: str | list[str] | None = None)", "category": "reduction"},
    "sum_reduce": {"signature": "(dim: str)", "category": "reduction"},
    "max_reduce": {"signature": "(dim: str)", "category": "reduction"},
    "mean_reduce": {"signature": "(dim: str)", "category": "reduction"},
}

XARRAY_DENYLIST: frozenset[str] = frozenset({"values", "to_numpy", "load", "compute", "data"})


def is_allowed_method(method_name: str) -> bool:
    """
    Check if a method name is allowed for dynamic tool generation.

    Args:
        method_name: The name of the method to check.

    Returns:
        True if the method is in XARRAY_ALLOWLIST and not in XARRAY_DENYLIST.
    """
    return method_name in XARRAY_ALLOWLIST and method_name not in XARRAY_DENYLIST
