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
    reader = getattr(image, "reader", image)
    dims_obj = getattr(reader, "dims", None)
    axes = getattr(reader, "axes", None)
    if not axes and dims_obj and hasattr(dims_obj, "order"):
        axes = dims_obj.order

    shape = list(getattr(reader, "shape", ()))
    ndim = getattr(reader, "ndim", len(shape))
    axes_inferred = not bool(dims_obj)

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

    channel_names = getattr(image, "channel_names", None)
    if channel_names:
        meta["channel_names"] = [str(name) for name in channel_names]

    pps = getattr(image, "physical_pixel_sizes", None)
    if pps:
        meta["physical_pixel_sizes"] = {
            k: float(v) for k, v in {"X": pps.X, "Y": pps.Y, "Z": pps.Z}.items() if v is not None
        }

    return meta


def _extract_metadata_tifffile(path: Path) -> dict | None:
    """Fallback metadata extraction using tifffile."""
    try:
        import tifffile

        if not path.exists():
            return None

        with tifffile.TiffFile(path) as tif:
            # Get shape of first series
            series = tif.series[0]
            shape = list(series.shape)
            dtype = str(series.dtype)

            return {
                "ndim": len(shape),
                "shape": shape,
                "dtype": dtype,
                "axes": getattr(series, "axes", ""),
                "file_size_bytes": path.stat().st_size,
            }
    except Exception:  # noqa: BLE001
        if path.exists():
            return {"file_size_bytes": path.stat().st_size}
        return None


def extract_table_metadata(path: Path) -> dict | None:
    """Extract metadata from a CSV/TSV table file.

    Returns:
        {"columns": [{"name": "label", "dtype": "int64"}, ...], "row_count": 42}
    """
    import csv

    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            # Detect delimiter (CSV or TSV)
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample) if sample else None
            reader = csv.DictReader(f, dialect=dialect) if dialect else csv.DictReader(f)

            columns = []
            fieldnames = reader.fieldnames or []

            # Try to get first row for type inference
            first_row = next(reader, None)

            for name in fieldnames:
                dtype = "string"  # Default
                if first_row and name in first_row:
                    val = first_row[name]
                    if val is not None and val != "":
                        # Try int
                        try:
                            int(val)
                            dtype = "int64"
                        except ValueError:
                            # Try float
                            try:
                                float(val)
                                dtype = "float64"
                            except ValueError:
                                dtype = "string"

                columns.append({"name": name, "dtype": dtype})

            # Count remaining rows
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
