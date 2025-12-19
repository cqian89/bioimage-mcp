from __future__ import annotations

from pathlib import Path


def _uri_to_path(uri: str) -> Path:
    if uri.startswith("file://"):
        path_str = uri[7:]
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]
        return Path(path_str)
    return Path(uri)


def convert_to_ome_zarr(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    _ = params
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    in_path = _uri_to_path(str(uri))

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


def export_ome_tiff(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    in_path = _uri_to_path(str(uri))
    compression = params.get("compression")

    try:
        from bioio import BioImage  # type: ignore
        from bioio.writers import OmeTiffWriter  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for export_ome_tiff") from exc

    img = BioImage(str(in_path))
    data = img.get_image_data()  # type: ignore[attr-defined]

    out_path = work_dir / "export.ome.tiff"
    if out_path.exists():
        raise FileExistsError(out_path)

    OmeTiffWriter.save(data, str(out_path), compression=compression)
    return out_path
