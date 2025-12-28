from __future__ import annotations

from pathlib import Path


def _load_image_fallback(path: Path):
    warnings: list[dict[str, str]] = []

    try:
        from bioio import BioImage  # type: ignore
        from bioio_ome_tiff import Reader as OmeTiffReader  # type: ignore

        img = BioImage(str(path), reader=OmeTiffReader)
        return img.get_image_data(), warnings, "bioio-ome-tiff"
    except Exception as exc:
        warnings.append(
            {
                "code": "OME_TIFF_FALLBACK",
                "message": f"bioio-ome-tiff failed: {exc}",
            }
        )

    try:
        from bioio import BioImage  # type: ignore
        from bioio_bioformats import Reader as BioformatsReader  # type: ignore

        img = BioImage(str(path), reader=BioformatsReader)
        return img.get_image_data(), warnings, "bioio-bioformats"
    except Exception as exc:
        warnings.append(
            {
                "code": "BIOFORMATS_FALLBACK",
                "message": f"bioio-bioformats failed: {exc}",
            }
        )

    warnings.append(
        {
            "code": "TIFFFILE_FALLBACK",
            "message": "Using tifffile - metadata may be incomplete",
        }
    )
    import tifffile

    return tifffile.imread(str(path)), warnings, "tifffile"


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
    except Exception as exc:
        raise RuntimeError("Missing dependencies for convert_to_ome_zarr") from exc

    try:
        from bioio import BioImage  # type: ignore

        img = BioImage(str(in_path))
        data = img.get_image_data()  # type: ignore[attr-defined]
    except Exception:
        data, _, _ = _load_image_fallback(in_path)

    out_dir = work_dir / "converted.ome.zarr"
    if out_dir.exists():
        raise FileExistsError(out_dir)

    root = zarr.open_group(str(out_dir), mode="w")
    root.create_array("0", data=data, chunks=data.shape)

    return out_dir
