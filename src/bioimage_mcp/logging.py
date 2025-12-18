from __future__ import annotations

import logging
import os

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%dT%H:%M:%S"


def configure_logging(level: str | None = None) -> None:
    """Configure logging once for CLI-friendly output."""

    resolved_level = (level or os.environ.get("BIOIMAGE_MCP_LOG_LEVEL") or "INFO").upper()

    root = logging.getLogger("bioimage_mcp")
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT))

    root.addHandler(handler)
    root.setLevel(resolved_level)
    root.propagate = False


def get_logger(name: str = "bioimage_mcp") -> logging.Logger:
    """Return a configured logger."""

    configure_logging()
    return logging.getLogger(name)
