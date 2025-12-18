from __future__ import annotations

from pathlib import Path


def gaussian_blur(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    """Gaussian blur using scipy; writes OME-Zarr output."""

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri or not str(uri).startswith("file://"):
        raise ValueError("Input 'image' must be a file:// BioImageRef")

    sigma = float(params.get("sigma", 1.0))
    in_path = Path(str(uri).replace("file://", ""))

    try:
        import zarr
        from bioio import BioImage  # type: ignore
        from scipy.ndimage import gaussian_filter
    except Exception as exc:
        raise RuntimeError("Missing dependencies for gaussian_blur") from exc

    img = BioImage(str(in_path))
    data = img.get_image_data("ZYX")  # type: ignore[attr-defined]

    blurred = gaussian_filter(data.astype("float32"), sigma=sigma)

    out_dir = work_dir / "blurred.ome.zarr"
    if out_dir.exists():
        raise FileExistsError(out_dir)

    root = zarr.open_group(str(out_dir), mode="w")
    root.create_dataset("0", data=blurred, chunks=True)
    (out_dir / ".bioimage_mcp_axes").write_text("ZYX")

    return out_dir
