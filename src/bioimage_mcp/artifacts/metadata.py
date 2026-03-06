from __future__ import annotations

from pathlib import Path
from typing import Any


def _truncate_text(value: str, limit: int = 1024) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... ({len(value)} chars)"


def _truncate_dict(
    value: dict,
    *,
    max_keys: int = 20,
    max_string: int = 500,
    max_depth: int = 2,
) -> dict:
    truncated = False

    def truncate_value(item: Any, depth: int) -> Any:
        nonlocal truncated
        if isinstance(item, str):
            if len(item) > max_string:
                truncated = True
                return item[:max_string]
            return item
        if depth >= max_depth:
            if isinstance(item, (dict, list, tuple)):
                truncated = True
                return "..."
            return item
        if isinstance(item, dict):
            result: dict = {}
            for idx, (key, nested) in enumerate(item.items()):
                if idx >= max_keys:
                    truncated = True
                    break
                result[str(key)] = truncate_value(nested, depth + 1)
            return result
        if isinstance(item, (list, tuple)):
            return [truncate_value(nested, depth + 1) for nested in item]
        return item

    result = truncate_value(value, 0)
    if not isinstance(result, dict):
        return {}

    if truncated:
        if "_truncated" not in result:
            if len(result) >= max_keys:
                last_key = next(reversed(result))
                result.pop(last_key)
            result["_truncated"] = True
        else:
            result["_truncated"] = True

    return result


def _safe_get_ome_metadata(image: Any) -> Any | None:
    try:
        return image.ome_metadata
    except NotImplementedError:
        return None
    except Exception:  # noqa: BLE001
        return None


def _extract_ome_xml_summary(image: Any) -> str:
    ome_meta = _safe_get_ome_metadata(image)
    if ome_meta is None:
        return ""

    xml = ""
    if hasattr(ome_meta, "to_xml"):
        try:
            xml = ome_meta.to_xml()
        except Exception:  # noqa: BLE001
            xml = ""
    elif hasattr(ome_meta, "to_xml_string"):
        try:
            xml = ome_meta.to_xml_string()
        except Exception:  # noqa: BLE001
            xml = ""

    if not xml:
        try:
            xml = str(ome_meta)
        except Exception:  # noqa: BLE001
            xml = ""

    return _truncate_text(xml)


def _extract_custom_attributes(image: Any) -> dict:
    custom_attributes = getattr(image, "custom_attributes", None)
    if isinstance(custom_attributes, dict):
        return custom_attributes

    candidate = getattr(image, "metadata", None)
    if candidate is not None:
        if hasattr(candidate, "to_dict"):
            try:
                candidate = candidate.to_dict()
            except Exception:  # noqa: BLE001
                candidate = None
        if isinstance(candidate, dict):
            for key in ("custom_attributes", "vendor_metadata", "vendor_specific"):
                value = candidate.get(key)
                if isinstance(value, dict):
                    return value

    ome_meta = _safe_get_ome_metadata(image)
    if ome_meta is not None and hasattr(ome_meta, "to_dict"):
        try:
            ome_dict = ome_meta.to_dict()
        except Exception:  # noqa: BLE001
            ome_dict = None
        if isinstance(ome_dict, dict):
            for key in ("structured_annotations", "structuredAnnotations"):
                value = ome_dict.get(key)
                if isinstance(value, dict):
                    return value

    return {}


def extract_image_metadata(path: Path) -> dict | None:
    """Extract metadata from an image file.

    Returns minimal metadata if bioio is not available in the environment.
    Returns None if the file doesn't exist or metadata cannot be extracted.

    Args:
        path: Path to the image file

    Returns:
        Dictionary with image metadata, or None if extraction failed
    """
    if path.name.lower().endswith((".tif", ".tiff")):
        return _extract_metadata_tifffile(path)

    # Try to import bioio - it may not be available in core environment
    try:
        from bioio import BioImage  # type: ignore
    except ImportError:
        # bioio not available in core environment, try tifffile as fallback
        return _extract_metadata_tifffile(path)

    # bioio is available, try to extract full metadata
    try:
        image = BioImage(str(path))
    except Exception:
        # If BioImage fails, try tifffile fallback
        return _extract_metadata_tifffile(path)

    # Use reader for native dimensions (T021)
    try:
        reader = getattr(image, "reader", image)
        dims_obj = getattr(reader, "dims", None)
        axes = getattr(reader, "axes", None)
        if not axes and dims_obj and hasattr(dims_obj, "order"):
            axes = dims_obj.order

        shape = list(getattr(reader, "shape", ()))
        ndim = getattr(reader, "ndim", len(shape))
        axes_inferred = not bool(dims_obj)
    except Exception:
        return None

    # Keep this intentionally minimal and JSON-serializable.
    meta: dict = {
        "axes": axes or "",
        "ndim": ndim,
        "dims": list(axes) if axes else [],
        "shape": shape,
        "dtype": str(getattr(reader, "dtype", "")),
        "axes_inferred": axes_inferred,
        "file_metadata": {
            "ome_xml_summary": _extract_ome_xml_summary(image),
            "custom_attributes": _truncate_dict(_extract_custom_attributes(image)),
        },
    }

    try:
        channel_names = getattr(image, "channel_names", None)
        if channel_names:
            meta["channel_names"] = [str(name) for name in channel_names]
    except Exception:
        pass

    try:
        pps = getattr(image, "physical_pixel_sizes", None)
        if pps:
            meta["physical_pixel_sizes"] = {
                k: float(v)
                for k, v in {"X": pps.X, "Y": pps.Y, "Z": pps.Z}.items()
                if v is not None
            }
    except Exception:
        pass

    return meta


def _extract_metadata_tifffile(path: Path) -> dict | None:
    """Fallback metadata extraction using tifffile."""
    try:
        import re

        import tifffile

        if not path.exists():
            return None

        with tifffile.TiffFile(path) as tif:
            # Get shape of first series
            if not tif.series:
                return {
                    "axes": "",
                    "ndim": 0,
                    "dims": [],
                    "shape": [],
                    "dtype": "",
                    "axes_inferred": True,
                    "file_metadata": {
                        "ome_xml_summary": "",
                        "custom_attributes": {},
                    },
                    "file_size_bytes": path.stat().st_size,
                }

            series = tif.series[0]
            shape = list(series.shape)
            dtype = str(series.dtype)
            axes = getattr(series, "axes", "") or ""

            ome_xml = ""
            if tif.is_ome:
                ome_xml = getattr(tif, "ome_metadata", "")

            meta = {
                "axes": axes,
                "ndim": len(shape),
                "dims": list(axes),
                "shape": shape,
                "dtype": dtype,
                "axes_inferred": True,
                "file_metadata": {
                    "ome_xml_summary": _truncate_text(ome_xml) if ome_xml else "",
                    "custom_attributes": {},
                },
                "file_size_bytes": path.stat().st_size,
            }

            # If it is OME, try to get pixel sizes, channel names, and singleton dims.
            # tifffile collapses singleton axes in series.shape/series.axes, but for
            # artifact consistency we preserve the full OME Pixels sizes.
            if ome_xml:
                sizes: dict[str, int] = {}
                for dim in ("T", "C", "Z", "Y", "X"):
                    match = re.search(f'Size{dim}="(\\d+)"', ome_xml)
                    if match:
                        try:
                            sizes[dim] = int(match.group(1))
                        except ValueError:
                            pass

                if sizes:
                    # Prefer OME XML sizes, but fall back to the series shape if needed.
                    t = sizes.get("T", 1)
                    c = sizes.get("C", 1)
                    z = sizes.get("Z", 1)
                    y = sizes.get("Y", shape[-2] if len(shape) >= 2 else 1)
                    x = sizes.get("X", shape[-1] if len(shape) >= 1 else 1)

                    full_sizes = {"T": t, "C": c, "Z": z, "Y": y, "X": x}
                    new_axes = ""
                    new_shape = []

                    # Build axes string dynamically: include if size > 1 OR explicitly in the file axes
                    # Preserve ordering from tifffile if available
                    order = axes.upper() if axes else "TCZYX"
                    for ax in order:
                        if ax in full_sizes:
                            val = full_sizes[ax]
                            if val > 1 or (axes and ax in axes.upper()):
                                if ax not in new_axes:
                                    new_axes += ax
                                    new_shape.append(val)

                    # Fallback to YX if we have no axes but have data
                    if not new_axes:
                        new_axes = "YX"
                        new_shape = [y, x]

                    meta["axes"] = new_axes
                    meta["ndim"] = len(new_axes)
                    meta["dims"] = list(new_axes)
                    meta["shape"] = new_shape

                pps = {}
                for dim in ("X", "Y", "Z"):
                    match = re.search(f'PhysicalSize{dim}="([^"]+)"', ome_xml)
                    if match:
                        try:
                            pps[dim] = float(match.group(1))
                        except ValueError:
                            pass
                if pps:
                    meta["physical_pixel_sizes"] = pps

                channels = re.findall(r'Channel [^>]*Name="([^"]+)"', ome_xml)
                if not channels:
                    channels = re.findall(r'Channel [^>]*ID="([^"]+)"', ome_xml)
                if channels:
                    meta["channel_names"] = channels

            return meta
    except Exception:  # noqa: BLE001
        if path.exists():
            return {
                "axes": "",
                "ndim": 0,
                "dims": [],
                "shape": [],
                "dtype": "",
                "axes_inferred": True,
                "file_metadata": {
                    "ome_xml_summary": "",
                    "custom_attributes": {},
                },
                "file_size_bytes": path.stat().st_size,
            }
        return None


def extract_table_metadata(path: Path) -> dict | None:
    """Extract metadata from a CSV/TSV table file.

    Returns:
        {"columns": [{"name": "label", "dtype": "int64"}, ...], "row_count": 42}
    """
    import csv

    def infer_dtype(value: str | None) -> str:
        if value is None or value == "":
            return "string"
        try:
            int(value)
            return "int64"
        except ValueError:
            try:
                float(value)
                return "float64"
            except ValueError:
                return "string"

    if not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8")
        if not text:
            return None

        lines = text.splitlines()
        if not lines:
            return None

        header_line = lines[0]
        row_lines = lines[1:]

        single_column = "," not in header_line and "\t" not in header_line
        if single_column:
            column_name = header_line.strip()
            if not column_name:
                return None
            first_value = next((line.strip() for line in row_lines if line.strip() != ""), None)
            return {
                "columns": [{"name": column_name, "dtype": infer_dtype(first_value)}],
                "row_count": sum(1 for line in row_lines if line.strip() != ""),
            }

        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample) if sample else None
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, dialect=dialect) if dialect else csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            first_row = next(reader, None)

            columns = [
                {"name": name, "dtype": infer_dtype(first_row.get(name) if first_row else None)}
                for name in fieldnames
            ]
            row_count = (1 if first_row else 0) + sum(1 for _ in reader)

        return {"columns": columns, "row_count": row_count}
    except Exception:  # noqa: BLE001
        return None


def get_ndim(metadata: dict) -> int:
    """Get ndim with fallback for legacy artifacts."""
    if "ndim" in metadata:
        return int(metadata["ndim"])
    if "shape" in metadata:
        return len(metadata["shape"])
    if "axes" in metadata:
        return len(metadata["axes"])
    return 5  # Legacy default
