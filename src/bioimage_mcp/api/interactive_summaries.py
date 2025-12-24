from bioimage_mcp.artifacts.models import ArtifactRef


def summarize_artifact(ref: ArtifactRef) -> dict:
    """Summarize an artifact for interactive display.

    Args:
        ref: The artifact reference to summarize.

    Returns:
        A dictionary containing summary information.
        Always includes 'type' and 'size_bytes'.
        May include 'shape' and 'dtype' if available in metadata.
    """
    summary = {
        "type": ref.type,
        "size_bytes": ref.size_bytes,
    }

    if "shape" in ref.metadata:
        summary["shape"] = ref.metadata["shape"]

    if "dtype" in ref.metadata:
        summary["dtype"] = ref.metadata["dtype"]

    return summary
