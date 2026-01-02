from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from bioimage_mcp_base.utils import (
    load_image,
    resolve_axis,
    save_zarr,
    uri_to_path,
)


def _assert_read_allowed(path: Path) -> None:
    allowlist = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_READ")
    if not allowlist:
        return

    try:
        roots = json.loads(allowlist)
    except json.JSONDecodeError:
        return

    target = path.expanduser().absolute()
    for root in roots:
        root_path = Path(root).expanduser().absolute()
        try:
            target.relative_to(root_path)
            return
        except ValueError:
            continue

    raise PermissionError(f"Path not under allowlist read roots: {target}")


def flip(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis")
    if axis is None:
        raise ValueError("'axis' is required")

    image_ref.get("format")
    data = load_image(uri_to_path(str(uri)))
    idx = resolve_axis(axis, data.ndim)
    flipped = np.flip(data, axis=idx)
    return save_zarr(flipped, work_dir, "flipped.ome.zarr")


def crop(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    start = params.get("start")
    stop = params.get("stop")
    if start is None or stop is None:
        raise ValueError("'start' and 'stop' are required")

    image_ref.get("format")
    data = load_image(uri_to_path(str(uri)))
    if len(start) != data.ndim or len(stop) != data.ndim:
        raise ValueError("'start' and 'stop' must match image dimensions")

    slices = tuple(slice(int(s), int(e)) for s, e in zip(start, stop, strict=True))
    cropped = data[slices]
    return save_zarr(cropped, work_dir, "cropped.ome.zarr")


def pad(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    pad_width = params.get("pad_width")
    if pad_width is None:
        raise ValueError("'pad_width' is required")

    mode = params.get("mode", "constant")
    constant_values = params.get("constant_values", 0)

    image_ref.get("format")
    data = load_image(uri_to_path(str(uri)))
    padded = np.pad(data, pad_width=pad_width, mode=mode, constant_values=constant_values)
    return save_zarr(padded, work_dir, "padded.ome.zarr")


def project_sum(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", 0)
    path = uri_to_path(str(uri))
    _assert_read_allowed(path)
    image_ref.get("format")
    data = load_image(path)
    idx = resolve_axis(axis, data.ndim)
    projected = np.sum(data, axis=idx)
    return save_zarr(projected, work_dir, "project_sum.ome.zarr")


def project_max(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", 0)
    image_ref.get("format")
    data = load_image(uri_to_path(str(uri)))
    idx = resolve_axis(axis, data.ndim)
    projected = np.max(data, axis=idx)
    return save_zarr(projected, work_dir, "project_max.ome.zarr")
