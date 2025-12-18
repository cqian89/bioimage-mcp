from __future__ import annotations

from pathlib import Path


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

    # Keep this intentionally minimal and JSON-serializable.
    meta: dict = {
        "axes": getattr(image, "axes", None) or "",
        "shape": list(getattr(image, "shape", ()) or ()),
        "dtype": str(getattr(image, "dtype", "")),
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
