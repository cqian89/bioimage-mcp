"""Bioimage I/O functions for base toolkit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class PathNotAllowedError(Exception):
    """Raised when path is outside allowed paths."""

    def __init__(self, path: str, allowed_paths: list[str], mode: str = "read"):
        self.path = path
        self.allowed_paths = allowed_paths
        self.mode = mode
        self.code = "PATH_NOT_ALLOWED"
        super().__init__(f"Path '{path}' is not in allowed {mode} paths")


class FileNotFoundError(Exception):
    """Raised when file does not exist."""

    def __init__(self, path: str):
        self.path = path
        self.code = "FILE_NOT_FOUND"
        super().__init__(f"File not found: {path}")


class UnsupportedFormatError(Exception):
    """Raised when format is not supported."""

    def __init__(self, path: str, format_hint: str | None = None):
        self.path = path
        self.format_hint = format_hint
        self.code = "UNSUPPORTED_FORMAT"
        super().__init__(f"Unsupported format for: {path}")


class ValidationFailedError(Exception):
    """Raised when file validation fails."""

    def __init__(self, path: str, issues: list[str]):
        self.path = path
        self.issues = issues
        self.code = "VALIDATION_FAILED"
        super().__init__(f"Validation failed for: {path}")


class SliceOutOfBoundsError(Exception):
    """Raised when slice indices exceed array dimensions."""

    def __init__(self, dim: str, index: int, size: int):
        self.dim = dim
        self.index = index
        self.size = size
        self.code = "SLICE_OUT_OF_BOUNDS"
        super().__init__(f"Slice index {index} exceeds dimension {dim} size {size}")


def validate_read_path(path: str, allowed_paths: list[str] | None = None) -> Path:
    """Validate that path is within allowed read paths.

    Args:
        path: Path to validate
        allowed_paths: List of allowed path prefixes. If None, reads from environment.

    Returns:
        The resolved Path object.

    Raises:
        PathNotAllowedError: If path is not within any allowed path
    """
    if allowed_paths is None:
        allowed_paths = _get_allowed_read_paths()

    path_obj = Path(path).resolve()
    for allowed in allowed_paths:
        allowed_obj = Path(allowed).resolve()
        try:
            path_obj.relative_to(allowed_obj)
            return path_obj  # Path is within allowed path
        except ValueError:
            continue

    raise PathNotAllowedError(str(path_obj), allowed_paths, mode="read")


def validate_write_path(path: str, allowed_paths: list[str] | None = None) -> Path:
    """Validate that path is within allowed write paths.

    Args:
        path: Path to validate
        allowed_paths: List of allowed path prefixes. If None, reads from environment.

    Returns:
        The resolved Path object.

    Raises:
        PathNotAllowedError: If path is not within any allowed path
    """
    if allowed_paths is None:
        allowed_paths = _get_allowed_write_paths()

    path_obj = Path(path).resolve()
    for allowed in allowed_paths:
        allowed_obj = Path(allowed).resolve()
        try:
            path_obj.relative_to(allowed_obj)
            return path_obj
        except ValueError:
            continue

    raise PathNotAllowedError(str(path_obj), allowed_paths, mode="write")


def _get_allowed_read_paths() -> list[str]:
    """Get allowed read paths from environment."""
    env_val = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_READ", "[]")
    try:
        return json.loads(env_val)
    except json.JSONDecodeError:
        return []


def _get_allowed_write_paths() -> list[str]:
    """Get allowed write paths from environment."""
    env_val = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", "[]")
    try:
        return json.loads(env_val)
    except json.JSONDecodeError:
        return []


def make_error_response(error: Exception) -> dict[str, Any]:
    """Create structured error response from exception.

    Args:
        error: Exception with code attribute

    Returns:
        Dict with error shape matching quickstart.md format
    """
    code = getattr(error, "code", "UNKNOWN_ERROR")
    message = str(error)

    details = {}
    if isinstance(error, PathNotAllowedError):
        details["allowed_paths"] = error.allowed_paths
        details["mode"] = error.mode
    elif isinstance(error, ValidationFailedError):
        details["issues"] = error.issues
        # Test compatibility: tests expect 'reason' in details
        if error.issues:
            details["reason"] = error.issues[0]
    elif isinstance(error, SliceOutOfBoundsError):
        details["dimension"] = error.dim
        details["index"] = error.index
        details["size"] = error.size

    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


# Test helper functions (imported by tests/unit/api/test_io_functions.py)
def path_not_allowed_error(
    path: str, allowed_paths: list[str], mode: str = "read"
) -> dict[str, Any]:
    return make_error_response(PathNotAllowedError(path, allowed_paths, mode))


def file_not_found_error(path: str) -> dict[str, Any]:
    return make_error_response(FileNotFoundError(path))


def unsupported_format_error(path: str, format_hint: str | None = None) -> dict[str, Any]:
    return make_error_response(UnsupportedFormatError(path, format_hint))


def validation_failed_error(path: str, reason: str) -> dict[str, Any]:
    return make_error_response(ValidationFailedError(path, [reason]))


def load(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Load an image file into the artifact system."""
    raise NotImplementedError("base.io.bioimage.load not yet implemented")


def inspect(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Extract metadata from an image without loading pixel data."""
    raise NotImplementedError("base.io.bioimage.inspect not yet implemented")


def slice_image(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Extract a subset of a multi-dimensional image."""
    raise NotImplementedError("base.io.bioimage.slice not yet implemented")


def validate(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Validate an image file and report issues."""
    raise NotImplementedError("base.io.bioimage.validate not yet implemented")


def get_supported_formats(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Return list of supported image formats."""
    raise NotImplementedError("base.io.bioimage.get_supported_formats not yet implemented")


def export(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Export an artifact to a specific file format."""
    raise NotImplementedError("base.io.bioimage.export not yet implemented")
