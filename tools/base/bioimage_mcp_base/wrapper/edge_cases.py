"""Edge case wrappers for transforms and preprocessing.

These functions require custom handling (e.g., axis parameters, coordinate
slicing) that cannot be directly mapped to library functions via dynamic
discovery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.preprocess import normalize_intensity as _normalize_intensity
from bioimage_mcp_base.transforms import (
    crop as _crop,
)
from bioimage_mcp_base.transforms import (
    flip as _flip,
)
from bioimage_mcp_base.transforms import (
    pad as _pad,
)
from bioimage_mcp_base.transforms import (
    project_max as _project_max,
)
from bioimage_mcp_base.transforms import (
    project_sum as _project_sum,
)


def _wrap_path_result(result: Path, format: str = "OME-Zarr") -> dict[str, Any]:
    """Wrap a Path result in a standardized output dict."""
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": format,
                "path": str(result),
            }
        },
        "warnings": [],
        "log": "ok",
    }


def crop(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Crop an image using pixel coordinates."""
    result = _crop(inputs=inputs, params=params, work_dir=work_dir)
    return _wrap_path_result(result)


def normalize_intensity(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Normalize image intensities using percentile-based scaling."""
    result = _normalize_intensity(inputs=inputs, params=params, work_dir=work_dir)
    return _wrap_path_result(result)


def project_sum(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Reduce a stack by summing over a selected axis."""
    result = _project_sum(inputs=inputs, params=params, work_dir=work_dir)
    return _wrap_path_result(result)


def project_max(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Reduce a stack by max projection over a selected axis."""
    result = _project_max(inputs=inputs, params=params, work_dir=work_dir)
    return _wrap_path_result(result)


def flip(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Flip an image along an axis."""
    result = _flip(inputs=inputs, params=params, work_dir=work_dir)
    return _wrap_path_result(result)


def pad(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Pad an image to a target shape."""
    result = _pad(inputs=inputs, params=params, work_dir=work_dir)
    return _wrap_path_result(result)
