from __future__ import annotations

from typing import Any


def record_artifact_dimensions(
    provenance: dict[str, Any], key: str, artifact_ref: dict[str, Any]
) -> None:
    """Add dimension metadata for an artifact to provenance (T028a).

    Args:
        provenance: The provenance dictionary to update
        key: The key under which to store the dimensions (e.g. 'input.image', 'output.mask')
        artifact_ref: The artifact reference containing dimension metadata
    """
    dims_meta = {}
    for field in ["ndim", "dims", "shape", "dtype"]:
        # Check top-level first, then metadata dict
        val = artifact_ref.get(field)
        if val is None and "metadata" in artifact_ref:
            val = artifact_ref["metadata"].get(field)

        if val is not None:
            dims_meta[field] = val

    if dims_meta:
        if "dimensions" not in provenance:
            provenance["dimensions"] = {}
        provenance["dimensions"][key] = dims_meta
