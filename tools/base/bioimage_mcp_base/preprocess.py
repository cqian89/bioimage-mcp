from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from bioimage_mcp_base.utils import load_image, resolve_axis, save_zarr, uri_to_path


def normalize_intensity(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    pmin = float(params.get("pmin", 1))
    pmax = float(params.get("pmax", 99.8))
    clip = bool(params.get("clip", True))

    data = load_image(uri_to_path(str(uri))).astype("float32")
    vmin, vmax = np.percentile(data, (pmin, pmax))
    scaled = (data - vmin) / (vmax - vmin) if vmax != vmin else data
    if clip:
        scaled = np.clip(scaled, 0, 1)
    return save_zarr(scaled, work_dir, "normalized.ome.zarr")


def gaussian(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.filters import gaussian as sk_gaussian

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    sigma = params.get("sigma", 1.0)
    preserve_range = bool(params.get("preserve_range", True))

    data = load_image(uri_to_path(str(uri)))
    blurred = sk_gaussian(data, sigma=sigma, preserve_range=preserve_range)
    return save_zarr(blurred, work_dir, "gaussian.ome.zarr")


def median(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.filters import median as sk_median
    from skimage.morphology import ball, disk

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    radius = int(params.get("radius", 1))
    data = load_image(uri_to_path(str(uri)))
    footprint = disk(radius) if data.ndim == 2 else ball(radius)
    filtered = sk_median(data, footprint=footprint)
    return save_zarr(filtered, work_dir, "median.ome.zarr")


def bilateral(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.restoration import denoise_bilateral

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    sigma_color = params.get("sigma_color", 0.05)
    sigma_spatial = params.get("sigma_spatial", 15)
    channel_axis = params.get("channel_axis", None)

    data = load_image(uri_to_path(str(uri))).astype("float32")
    filtered = denoise_bilateral(
        data,
        sigma_color=sigma_color,
        sigma_spatial=sigma_spatial,
        channel_axis=channel_axis,
    )
    return save_zarr(filtered, work_dir, "bilateral.ome.zarr")


def sobel(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.filters import sobel as sk_sobel

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", None)
    data = load_image(uri_to_path(str(uri)))
    if axis is not None:
        idx = resolve_axis(axis, data.ndim)
        edges = sk_sobel(data, axis=idx)
    else:
        edges = sk_sobel(data)
    return save_zarr(edges, work_dir, "sobel.ome.zarr")


def denoise_nl_means(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.restoration import denoise_nl_means

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    patch_size = int(params.get("patch_size", 5))
    patch_distance = int(params.get("patch_distance", 6))
    h = params.get("h", 0.1)

    data = load_image(uri_to_path(str(uri))).astype("float32")
    denoised = denoise_nl_means(
        data,
        patch_size=patch_size,
        patch_distance=patch_distance,
        h=h,
        fast_mode=True,
        channel_axis=None,
    )
    return save_zarr(denoised, work_dir, "denoise_nl_means.ome.zarr")


def unsharp_mask(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.filters import unsharp_mask as sk_unsharp

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    radius = float(params.get("radius", 1.0))
    amount = float(params.get("amount", 1.0))
    preserve_range = bool(params.get("preserve_range", True))

    data = load_image(uri_to_path(str(uri)))
    sharpened = sk_unsharp(data, radius=radius, amount=amount, preserve_range=preserve_range)
    return save_zarr(sharpened, work_dir, "unsharp_mask.ome.zarr")


def equalize_adapthist(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.exposure import equalize_adapthist as sk_equalize

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    kernel_size = params.get("kernel_size", None)
    clip_limit = params.get("clip_limit", 0.01)

    data = load_image(uri_to_path(str(uri))).astype("float32")
    eq = sk_equalize(data, kernel_size=kernel_size, clip_limit=clip_limit)
    return save_zarr(eq, work_dir, "equalize_adapthist.ome.zarr")


def threshold_otsu(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.filters import threshold_otsu as sk_otsu

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    apply = bool(params.get("apply", True))
    data = load_image(uri_to_path(str(uri)))
    thresh = sk_otsu(data)
    result = (data > thresh).astype("uint8") if apply else data
    return save_zarr(result, work_dir, "threshold_otsu.ome.zarr")


def threshold_yen(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.filters import threshold_yen as sk_yen

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    apply = bool(params.get("apply", True))
    data = load_image(uri_to_path(str(uri)))
    thresh = sk_yen(data)
    result = (data > thresh).astype("uint8") if apply else data
    return save_zarr(result, work_dir, "threshold_yen.ome.zarr")


def morph_opening(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.morphology import opening, ball, disk

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    radius = int(params.get("radius", 1))
    data = load_image(uri_to_path(str(uri)))
    selem = disk(radius) if data.ndim == 2 else ball(radius)
    opened = opening(data, selem)
    return save_zarr(opened, work_dir, "morph_opening.ome.zarr")


def morph_closing(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.morphology import closing, ball, disk

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    radius = int(params.get("radius", 1))
    data = load_image(uri_to_path(str(uri)))
    selem = disk(radius) if data.ndim == 2 else ball(radius)
    closed = closing(data, selem)
    return save_zarr(closed, work_dir, "morph_closing.ome.zarr")


def remove_small_objects(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.morphology import remove_small_objects as sk_remove

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    min_size = int(params.get("min_size", 64))
    connectivity = params.get("connectivity", 1)

    data = load_image(uri_to_path(str(uri)))
    cleaned = sk_remove(data.astype(bool), min_size=min_size, connectivity=connectivity)
    return save_zarr(cleaned.astype("uint8"), work_dir, "remove_small_objects.ome.zarr")
