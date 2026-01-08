"""Shared utilities for Cellpose operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a Path."""
    if uri.startswith("file://"):
        # Handle Windows paths that may have extra slash: file:///C:/...
        path_str = uri[7:]  # Remove file://
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]  # Remove leading / for Windows paths
        return Path(unquote(path_str))
    return Path(uri)


def _coerce_param(value: Any, param_type: type, param_name: str) -> Any:
    """Coerce parameter to expected type with helpful error messages.

    Args:
        value: The parameter value (might be wrong type)
        param_type: Expected type (int, float, bool)
        param_name: Name of parameter for error messages

    Returns:
        The value coerced to the expected type

    Raises:
        ValueError: If coercion fails
    """
    if value is None:
        return None

    if isinstance(value, param_type):
        return value

    try:
        if param_type is bool:
            # Handle string booleans
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        return param_type(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Parameter '{param_name}' must be {param_type.__name__}, "
            f"got {type(value).__name__}: {value!r}"
        ) from e
