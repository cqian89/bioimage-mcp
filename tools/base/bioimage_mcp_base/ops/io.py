"""Bioimage I/O functions for base toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import Any


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
