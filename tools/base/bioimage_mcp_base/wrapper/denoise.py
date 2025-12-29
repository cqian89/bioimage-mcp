from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.preprocess import denoise_image as _denoise_image


def denoise_image(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Thin wrapper for denoise_image."""
    return _denoise_image(inputs=inputs, params=params, work_dir=work_dir)
