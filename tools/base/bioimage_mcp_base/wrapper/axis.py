from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.axis_ops import (
    expand_dims as _expand_dims,
)
from bioimage_mcp_base.axis_ops import (
    moveaxis as _moveaxis,
)
from bioimage_mcp_base.axis_ops import (
    relabel_axes as _relabel_axes,
)
from bioimage_mcp_base.axis_ops import (
    squeeze as _squeeze,
)
from bioimage_mcp_base.axis_ops import (
    swap_axes as _swap_axes,
)


def relabel_axes(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Thin wrapper for relabel_axes."""
    return _relabel_axes(inputs=inputs, params=params, work_dir=work_dir)


def squeeze(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Thin wrapper for squeeze."""
    return _squeeze(inputs=inputs, params=params, work_dir=work_dir)


def expand_dims(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Thin wrapper for expand_dims."""
    return _expand_dims(inputs=inputs, params=params, work_dir=work_dir)


def moveaxis(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Thin wrapper for moveaxis."""
    return _moveaxis(inputs=inputs, params=params, work_dir=work_dir)


def swap_axes(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Thin wrapper for swap_axes."""
    return _swap_axes(inputs=inputs, params=params, work_dir=work_dir)
