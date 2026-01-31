from __future__ import annotations

import importlib.metadata
from functools import lru_cache


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the installed version of bioimage-mcp."""
    try:
        return importlib.metadata.version("bioimage-mcp")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"


__version__ = get_version()
