from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from bioimage_mcp_base.utils import load_image, save_zarr, uri_to_path


def normalize_intensity(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref if isinstance(image_ref, str) else image_ref.get("uri")
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


def _load_image_with_axes(image_ref: dict | str) -> tuple[np.ndarray, str]:
    uri = image_ref if isinstance(image_ref, str) else image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    path = uri_to_path(str(uri))
    if not path.exists():
        raise FileNotFoundError(f"Input image not found: {path}")

    if isinstance(image_ref, str):
        fmt = ""
    else:
        fmt = (image_ref.get("format") or "").lower()

    if "zarr" in fmt or path.suffix.lower() == ".zarr":
        raise ValueError(
            "OME-Zarr format is not supported. Convert to OME-TIFF first (base.export_ome_tiff)."
        )
    if fmt and "tiff" not in fmt:
        raise ValueError(f"Unsupported input format: {fmt}")
    if not fmt and path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Input must be an OME-TIFF (.tif/.tiff) file")

    try:
        from bioio import BioImage
    except Exception as exc:
        raise RuntimeError("Missing dependencies for denoise_image") from exc

    img = BioImage(str(path))
    data = img.reader.data
    if hasattr(data, "compute"):
        data = data.compute()

    if isinstance(image_ref, str):
        axes = ""
    else:
        axes = (image_ref.get("metadata") or {}).get("axes", "")

    if not axes:
        axes = img.reader.dims.order

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
    """Write array as OME-TIFF using bioio.writers.OmeTiffWriter."""
    from bioio.writers import OmeTiffWriter

    out_path = work_dir / name
    if out_path.exists():
        raise FileExistsError(out_path)

    OmeTiffWriter.save(array, str(out_path), dim_order=axes)
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
