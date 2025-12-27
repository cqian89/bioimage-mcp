from __future__ import annotations

from pathlib import Path
from typing import Any


def _truncate_text(value: str, limit: int = 1024) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _extract_ome_xml_summary(image: Any) -> str:
    ome_meta = getattr(image, "ome_metadata", None)
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

    ome_meta = getattr(image, "ome_metadata", None)
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


def extract_image_metadata(path: Path) -> dict:
    """Extract minimal BioImageRef metadata.

    Uses bioio when available. Falls back to an empty dict.
    """

    try:
        from bioio import BioImage  # type: ignore
    except Exception:
        return {}

    try:
        image = BioImage(str(path))
    except Exception:  # noqa: BLE001
        return {}

    dims = getattr(image, "dims", None)
    axes_inferred = not bool(dims)

    # Keep this intentionally minimal and JSON-serializable.
    meta: dict = {
        "axes": getattr(image, "axes", None) or "",
        "shape": list(getattr(image, "shape", ()) or ()),
        "dtype": str(getattr(image, "dtype", "")),
        "axes_inferred": axes_inferred,
        "file_metadata": {
            "ome_xml_summary": _extract_ome_xml_summary(image),
            "custom_attributes": _extract_custom_attributes(image),
        },
    }

    channel_names = getattr(image, "channel_names", None)
    if channel_names:
        meta["channel_names"] = list(channel_names)

    pps = getattr(image, "physical_pixel_sizes", None)
    if pps:
        meta["physical_pixel_sizes"] = {
            k: float(v) for k, v in {"X": pps.X, "Y": pps.Y, "Z": pps.Z}.items() if v is not None
        }

    return meta
