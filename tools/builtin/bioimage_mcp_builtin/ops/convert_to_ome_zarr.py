from __future__ import annotations

from pathlib import Path


def convert_to_ome_zarr(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    """Convert input image to OME-Zarr.

    This is intentionally minimal for v0.0; it relies on bioio plugins.
    """

    _ = params

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri or not str(uri).startswith("file://"):
        raise ValueError("Input 'image' must be a file:// BioImageRef")

    in_path = Path(str(uri).replace("file://", ""))

    try:
        import zarr
        from bioio import BioImage  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for convert_to_ome_zarr") from exc

    img = BioImage(str(in_path))
    data = img.get_image_data()  # type: ignore[attr-defined]

    out_dir = work_dir / "converted.ome.zarr"
    if out_dir.exists():
        raise FileExistsError(out_dir)

    root = zarr.open_group(str(out_dir), mode="w")
    root.create_dataset("0", data=data, chunks=True)

    return out_dir
