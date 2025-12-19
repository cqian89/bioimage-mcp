from __future__ import annotations

from pathlib import Path

import numpy as np

from bioimage_mcp_base.utils import load_image, resolve_axis, save_zarr, uri_to_path


def resize(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.transform import resize as sk_resize

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    output_shape = params.get("output_shape")
    if output_shape is None:
        raise ValueError("'output_shape' is required")

    preserve_range = bool(params.get("preserve_range", True))
    anti_aliasing = bool(params.get("anti_aliasing", True))

    data = load_image(uri_to_path(str(uri)))
    resized = sk_resize(
        data,
        output_shape=tuple(output_shape),
        preserve_range=preserve_range,
        anti_aliasing=anti_aliasing,
    )
    return save_zarr(resized, work_dir, "resized.ome.zarr")


def rescale(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.transform import rescale as sk_rescale

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    scale = params.get("scale")
    if scale is None:
        raise ValueError("'scale' is required")

    preserve_range = bool(params.get("preserve_range", True))
    anti_aliasing = bool(params.get("anti_aliasing", True))

    data = load_image(uri_to_path(str(uri)))
    rescaled = sk_rescale(
        data,
        scale=scale,
        preserve_range=preserve_range,
        anti_aliasing=anti_aliasing,
    )
    return save_zarr(rescaled, work_dir, "rescaled.ome.zarr")


def rotate(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.transform import rotate as sk_rotate

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    angle = params.get("angle")
    if angle is None:
        raise ValueError("'angle' is required")

    resize = bool(params.get("resize", False))
    preserve_range = bool(params.get("preserve_range", True))

    data = load_image(uri_to_path(str(uri)))
    rotated = sk_rotate(data, angle=float(angle), resize=resize, preserve_range=preserve_range)
    return save_zarr(rotated, work_dir, "rotated.ome.zarr")


def flip(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis")
    if axis is None:
        raise ValueError("'axis' is required")

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

    data = load_image(uri_to_path(str(uri)))
    if len(start) != data.ndim or len(stop) != data.ndim:
        raise ValueError("'start' and 'stop' must match image dimensions")

    slices = tuple(slice(int(s), int(e)) for s, e in zip(start, stop))
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

    data = load_image(uri_to_path(str(uri)))
    padded = np.pad(data, pad_width=pad_width, mode=mode, constant_values=constant_values)
    return save_zarr(padded, work_dir, "padded.ome.zarr")


def project_sum(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", 0)
    data = load_image(uri_to_path(str(uri)))
    idx = resolve_axis(axis, data.ndim)
    projected = np.sum(data, axis=idx)
    return save_zarr(projected, work_dir, "project_sum.ome.zarr")


def project_max(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", 0)
    data = load_image(uri_to_path(str(uri)))
    idx = resolve_axis(axis, data.ndim)
    projected = np.max(data, axis=idx)
    return save_zarr(projected, work_dir, "project_max.ome.zarr")
