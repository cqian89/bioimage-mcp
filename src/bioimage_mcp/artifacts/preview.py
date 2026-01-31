from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from bioio import BioImage
from PIL import Image


TAB20_RGB = [
    (31, 119, 180),
    (174, 199, 232),
    (255, 127, 14),
    (255, 187, 120),
    (44, 160, 44),
    (152, 223, 138),
    (214, 39, 40),
    (255, 152, 150),
    (148, 103, 189),
    (197, 176, 213),
    (140, 86, 75),
    (196, 156, 148),
    (227, 119, 194),
    (247, 182, 210),
    (127, 127, 127),
    (199, 199, 199),
    (188, 189, 34),
    (219, 219, 141),
    (23, 190, 207),
    (158, 218, 229),
]


def apply_tab20_colormap(label_array: np.ndarray) -> np.ndarray:
    """Apply TAB20 colormap to a 2D integer label array."""
    h, w = label_array.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    # Get unique labels excluding 0
    unique_labels = np.unique(label_array)
    unique_labels = unique_labels[unique_labels != 0]

    for label in unique_labels:
        # Map label N to TAB20_RGB[(N-1) % 20]
        color_idx = (int(label) - 1) % 20
        rgb = TAB20_RGB[color_idx]

        mask = label_array == label
        rgba[mask, 0:3] = rgb
        rgba[mask, 3] = 255

    return rgba


def get_label_metadata(label_array: np.ndarray) -> dict:
    """Compute region count and centroids for labels."""
    unique_labels = np.unique(label_array)
    unique_labels = unique_labels[unique_labels != 0]

    count = len(unique_labels)
    centroids = []

    for label in unique_labels:
        coords = np.where(label_array == label)
        if len(coords[0]) > 0:
            # (Y, X) centroids
            y_mean = float(np.mean(coords[0]))
            x_mean = float(np.mean(coords[1]))
            centroids.append((y_mean, x_mean))

    return {"region_count": count, "centroids": centroids}


def apply_projection(array: np.ndarray, axis: int, method: str) -> np.ndarray:
    """Apply projection along an axis."""
    if method == "max":
        return np.max(array, axis=axis)
    elif method == "mean":
        return np.mean(array, axis=axis)
    elif method == "sum":
        return np.sum(array, axis=axis)
    elif method == "min":
        return np.min(array, axis=axis)
    elif method == "slice":
        # Take middle index by default
        idx = array.shape[axis] // 2
        return np.take(array, idx, axis=axis)
    else:
        # Fallback to max if method unknown
        return np.max(array, axis=axis)


def reduce_to_2d(
    array: np.ndarray,
    dims: list[str],
    projection: str | dict,
    slice_indices: dict | None = None,
    channel: int | None = None,
) -> np.ndarray:
    """Reduce N-D array to 2D for preview."""
    # Work on a copy of dims and array as we reduce
    current_dims = list(dims)
    current_array = array

    # 1. Handle channel selection if C axis exists
    if "C" in current_dims:
        c_idx = current_dims.index("C")
        if channel is not None and channel < current_array.shape[c_idx]:
            current_array = np.take(current_array, channel, axis=c_idx)
        else:
            current_array = np.take(current_array, 0, axis=c_idx)
        current_dims.pop(c_idx)

    # 2. Reduce Z axis first
    if "Z" in current_dims:
        z_idx = current_dims.index("Z")
        method = "max"
        if isinstance(projection, dict):
            method = projection.get("Z", "max")
        elif isinstance(projection, str):
            method = projection

        # Override with slice_indices if provided and method is slice
        if method == "slice" and slice_indices and "Z" in slice_indices:
            idx = slice_indices["Z"]
            if idx < current_array.shape[z_idx]:
                current_array = np.take(current_array, idx, axis=z_idx)
            else:
                current_array = apply_projection(current_array, z_idx, "slice")
        else:
            current_array = apply_projection(current_array, z_idx, method)
        current_dims.pop(z_idx)

    # 3. Reduce T axis next
    if "T" in current_dims:
        t_idx = current_dims.index("T")
        method = "max"
        if isinstance(projection, dict):
            method = projection.get("T", "max")
        elif isinstance(projection, str):
            method = projection

        if method == "slice" and slice_indices and "T" in slice_indices:
            idx = slice_indices["T"]
            if idx < current_array.shape[t_idx]:
                current_array = np.take(current_array, idx, axis=t_idx)
            else:
                current_array = apply_projection(current_array, t_idx, "slice")
        else:
            current_array = apply_projection(current_array, t_idx, method)
        current_dims.pop(t_idx)

    # 4. Handle any other remaining non-XY axes (if any)
    while len(current_dims) > 2:
        # Just take the first slice of anything remaining that isn't X or Y
        found_other = False
        for i, d in enumerate(current_dims):
            if d not in ("X", "Y"):
                current_array = np.take(current_array, 0, axis=i)
                current_dims.pop(i)
                found_other = True
                break
        if not found_other:
            # If we only have X and Y (or weird names) and still > 2, something is wrong
            # but let's just break to avoid infinite loop
            break

    # Final squeeze to remove any length-1 axes
    return np.squeeze(current_array)


def normalize_to_uint8(array: np.ndarray) -> np.ndarray:
    """Map array values to 0-255 range."""
    # Ensure float for calculation
    arr = array.astype(np.float32)
    v_min = np.min(arr)
    v_max = np.max(arr)

    if v_max > v_min:
        arr = 255 * (arr - v_min) / (v_max - v_min)
    else:
        arr = np.zeros_like(arr)

    return arr.astype(np.uint8)


def resize_preserve_aspect(array: np.ndarray, max_size: int) -> np.ndarray:
    """Resize so largest dimension is max_size, preserving aspect ratio."""
    h, w = array.shape
    if h <= max_size and w <= max_size:
        return array

    if h > w:
        new_h = max_size
        new_w = int(w * (max_size / h))
    else:
        new_w = max_size
        new_h = int(h * (max_size / w))

    # Pillow expects (width, height)
    img = Image.fromarray(array)
    img = img.resize((new_w, new_h), resample=Image.BILINEAR)
    return np.array(img)


def encode_png_base64(array: np.ndarray) -> str:
    """Convert 2D uint8 array to PNG and return base64 string."""
    img = Image.fromarray(array)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_image_preview(
    path: Path,
    dims: list[str],
    shape: list[int],
    dtype: str,
    *,
    max_size: int = 256,
    projection: str | dict = "max",
    slice_indices: dict | None = None,
    channel: int | None = None,
) -> dict | None:
    """Main entry point for BioImageRef preview."""
    try:
        # Load image data using bioio
        # Note: we use BioImage to handle various formats
        img = BioImage(path)

        # bioio data property returns xarray-wrapped dask/numpy array
        # We want the underlying data for processing
        data = img.data.values

        # Reduce to 2D
        # bioio dims are typically TCZYX or similar
        img_dims = list(img.dims.order)
        arr_2d = reduce_to_2d(
            data,
            img_dims,
            projection=projection,
            slice_indices=slice_indices,
            channel=channel,
        )

        # Normalize
        arr_norm = normalize_to_uint8(arr_2d)

        # Resize
        arr_resized = resize_preserve_aspect(arr_norm, max_size)

        # Encode
        b64 = encode_png_base64(arr_resized)

        return {
            "base64": b64,
            "format": "png",
            "width": arr_resized.shape[1],
            "height": arr_resized.shape[0],
        }

    except Exception:
        # Fail silently per CONTEXT.md
        return None


def generate_label_preview(
    path: Path,
    dims: list[str],
    shape: list[int],
    dtype: str,
    *,
    max_size: int = 256,
    projection: str | dict = "max",
    slice_indices: dict | None = None,
    channel: int | None = None,
) -> dict | None:
    """Main entry point for LabelImageRef preview (colormap + metadata)."""
    try:
        img = BioImage(path)
        data = img.data.values
        img_dims = list(img.dims.order)

        # 1. Reduce to 2D
        arr_2d = reduce_to_2d(
            data,
            img_dims,
            projection=projection,
            slice_indices=slice_indices,
            channel=channel,
        )

        # 2. Get metadata before resizing
        meta = get_label_metadata(arr_2d)

        # 3. Apply colormap (RGBA)
        rgba = apply_tab20_colormap(arr_2d)

        # 4. Resize RGBA
        # resize_preserve_aspect needs to handle RGBA
        h, w, _ = rgba.shape
        if h > max_size or w > max_size:
            if h > w:
                new_h = max_size
                new_w = int(w * (max_size / h))
            else:
                new_w = max_size
                new_h = int(h * (max_size / w))
            img_pil = Image.fromarray(rgba, mode="RGBA")
            img_pil = img_pil.resize((new_w, new_h), resample=Image.NEAREST)
            rgba_resized = np.array(img_pil)
        else:
            rgba_resized = rgba

        # 5. Encode
        b64 = encode_png_base64(rgba_resized)

        return {
            "base64": b64,
            "format": "png",
            "width": rgba_resized.shape[1],
            "height": rgba_resized.shape[0],
            "region_count": meta["region_count"],
            "centroids": meta["centroids"],
        }

    except Exception:
        return None
