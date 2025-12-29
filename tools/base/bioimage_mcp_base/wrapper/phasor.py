from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.transforms import (
    phasor_calibrate as _phasor_calibrate,
)
from bioimage_mcp_base.transforms import (
    phasor_from_flim as _phasor_from_flim,
)


def phasor_from_flim(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Thin wrapper for phasor_from_flim."""
    return _phasor_from_flim(inputs=inputs, params=params, work_dir=work_dir)


def phasor_calibrate(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Thin wrapper for phasor_calibrate."""
    return _phasor_calibrate(inputs=inputs, params=params, work_dir=work_dir)
