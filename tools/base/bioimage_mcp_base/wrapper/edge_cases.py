from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.preprocess import normalize_intensity as _normalize_intensity
from bioimage_mcp_base.transforms import (
    crop as _crop,
    flip as _flip,
    pad as _pad,
    project_max as _project_max,
    project_sum as _project_sum,
)


def crop(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for crop."""
    return _crop(inputs=inputs, params=params, work_dir=work_dir)


def normalize_intensity(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for normalize_intensity."""
    return _normalize_intensity(inputs=inputs, params=params, work_dir=work_dir)


def project_sum(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for project_sum."""
    return _project_sum(inputs=inputs, params=params, work_dir=work_dir)


def project_max(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for project_max."""
    return _project_max(inputs=inputs, params=params, work_dir=work_dir)


def flip(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for flip."""
    return _flip(inputs=inputs, params=params, work_dir=work_dir)


def pad(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for pad."""
    return _pad(inputs=inputs, params=params, work_dir=work_dir)
