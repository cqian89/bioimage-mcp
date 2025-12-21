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


def _load_image_with_axes(image_ref: dict) -> tuple[np.ndarray, str]:
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    path = uri_to_path(str(uri))
    if not path.exists():
        raise FileNotFoundError(f"Input image not found: {path}")

    fmt = (image_ref.get("format") or "").lower()
    if "zarr" in fmt or path.suffix.lower() == ".zarr":
        raise ValueError(
            "OME-Zarr format is not supported. Convert to OME-TIFF first (base.export_ome_tiff)."
        )
    if fmt and "tiff" not in fmt:
        raise ValueError(f"Unsupported input format: {image_ref.get('format')}")
    if not fmt and path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Input must be an OME-TIFF (.tif/.tiff) file")

    try:
        from bioio import BioImage  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for denoise_image") from exc

    img = BioImage(str(path))
    data = img.get_image_data()  # type: ignore[attr-defined]
    axes = (image_ref.get("metadata") or {}).get("axes", "")
    if not axes:
        axes = getattr(img, "axes", "") or getattr(getattr(img, "dims", None), "order", "")

    axes = axes.upper() if axes else axes
    if not axes or len(axes) != data.ndim:
        raise ValueError("Input image must include axis metadata matching the data")

    return data, axes


def _validate_filter_params(filter_type: str, params: dict) -> None:
    allowed = {"filter_type", "method", "radius", "sigma", "sigma_color", "sigma_spatial"}
    unknown = set(params.keys()) - allowed
    if unknown:
        raise ValueError(f"Unsupported parameters: {sorted(unknown)}")

    if filter_type in {"median", "mean"}:
        if "sigma" in params:
            raise ValueError("sigma is only valid for gaussian filter")
        if "sigma_color" in params or "sigma_spatial" in params:
            raise ValueError("bilateral params are only valid for bilateral filter")
    elif filter_type == "gaussian":
        if "radius" in params:
            raise ValueError("radius is only valid for median or mean filters")
        if "sigma_color" in params or "sigma_spatial" in params:
            raise ValueError("bilateral params are only valid for bilateral filter")
    elif filter_type == "bilateral":
        if "radius" in params or "sigma" in params:
            raise ValueError("radius/sigma are not valid for bilateral filter")
    else:
        raise ValueError(f"Unsupported filter_type: {filter_type}")


def _apply_filter_2d(array: np.ndarray, filter_type: str, params: dict) -> np.ndarray:
    if filter_type == "median":
        from skimage.filters import median as sk_median
        from skimage.morphology import disk

        radius = int(params.get("radius", 1))
        return sk_median(array, footprint=disk(radius))

    if filter_type == "mean":
        from scipy.ndimage import uniform_filter

        radius = int(params.get("radius", 1))
        size = radius * 2 + 1
        return uniform_filter(array.astype("float32"), size=size)

    if filter_type == "gaussian":
        from skimage.filters import gaussian as sk_gaussian

        sigma = float(params.get("sigma", 1.0))
        return sk_gaussian(array, sigma=sigma, preserve_range=True)

    if filter_type == "bilateral":
        from skimage.restoration import denoise_bilateral

        sigma_color = float(params.get("sigma_color", 0.1))
        sigma_spatial = float(params.get("sigma_spatial", 1.0))
        return denoise_bilateral(
            array.astype("float32"),
            sigma_color=sigma_color,
            sigma_spatial=sigma_spatial,
            channel_axis=None,
        )

    raise ValueError(f"Unsupported filter_type: {filter_type}")


def _apply_filter_per_plane(
    data: np.ndarray,
    axes: str,
    filter_type: str,
    params: dict,
) -> np.ndarray:
    if "X" not in axes or "Y" not in axes:
        raise ValueError("Input image must include spatial X/Y axes")

    y_index = axes.index("Y")
    x_index = axes.index("X")

    order = [i for i in range(data.ndim) if i not in (y_index, x_index)] + [y_index, x_index]
    reordered = np.moveaxis(data, order, list(range(data.ndim)))

    leading_shape = reordered.shape[:-2]
    planes = reordered.reshape(-1, reordered.shape[-2], reordered.shape[-1])

    for idx in range(planes.shape[0]):
        planes[idx] = _apply_filter_2d(planes[idx], filter_type, params)

    filtered = planes.reshape(*leading_shape, reordered.shape[-2], reordered.shape[-1])
    return np.moveaxis(filtered, list(range(data.ndim)), order)


def _write_ome_tiff(
    array: np.ndarray,
    work_dir: Path,
    name: str,
    axes: str,
) -> Path:
    import tifffile

    out_path = work_dir / name
    if out_path.exists():
        raise FileExistsError(out_path)

    tifffile.imwrite(
        str(out_path),
        array,
        compression="zlib",
        photometric="minisblack",
        metadata={"axes": axes},
    )
    return out_path


def denoise_image(*, inputs: dict, params: dict, work_dir: Path) -> dict[str, Any]:
    image_ref = inputs.get("image") or {}
    data, axes = _load_image_with_axes(image_ref)

    filter_type = str(params.get("filter_type") or params.get("method") or "median").lower()
    _validate_filter_params(filter_type, params)

    filtered = _apply_filter_per_plane(data, axes, filter_type, params)
    out_path = _write_ome_tiff(
        np.asarray(filtered, dtype="float32"),
        work_dir,
        "denoised.ome.tiff",
        axes,
    )

    provenance = {
        "resolved_params": {
            "filter_type": filter_type,
            "radius": params.get("radius"),
            "sigma": params.get("sigma"),
            "sigma_color": params.get("sigma_color"),
            "sigma_spatial": params.get("sigma_spatial"),
        }
    }

    return {
        "outputs": {"output": {"type": "BioImageRef", "format": "OME-TIFF", "path": str(out_path)}},
        "warnings": [],
        "provenance": provenance,
        "log": f"denoise_image completed (filter_type={filter_type})",
    }
