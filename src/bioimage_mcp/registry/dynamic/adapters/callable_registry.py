from __future__ import annotations

import numpy as np
from typing import Any, Callable

# Curated allowlist of safe callable mappings
_SAFE_CALLABLES: dict[str, Callable[..., Any]] = {
    "min": np.min,
    "max": np.max,
    "mean": np.mean,
    "median": np.median,
    "std": np.std,
    "sum": np.sum,
    "numpy.min": np.min,
    "numpy.max": np.max,
    "numpy.mean": np.mean,
    "numpy.median": np.median,
    "numpy.std": np.std,
    "numpy.sum": np.sum,
}


def resolve_callable(ref: str) -> Callable[..., Any]:
    """
    Safely resolve a string reference to a callable from a curated allowlist.

    Args:
        ref: The string reference to resolve (e.g., "mean", "numpy.mean").

    Returns:
        The corresponding callable.

    Raises:
        ValueError: If the reference is not in the allowlist.
    """
    if ref in _SAFE_CALLABLES:
        return _SAFE_CALLABLES[ref]

    raise ValueError(
        f"Unauthorized or unknown callable reference: '{ref}'. "
        f"Allowed values are: {', '.join(sorted(_SAFE_CALLABLES.keys()))}"
    )
