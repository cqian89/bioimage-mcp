"""
Dynamic dispatch router for base tool pack.

Routes dynamic function calls (e.g., phasorpy.phasor.phasor_from_signal) to appropriate
adapters for execution. Handles artifact reference conversion between MCP
protocol (dict refs) and internal Artifact objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Import shared adapter registry populated with default adapters
from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY


def get_adapter_for_fn_id(fn_id: str) -> Any:
    """Find adapter for a given function ID by extracting prefix.

    Args:
        fn_id: Function identifier (e.g., "skimage.filters.gaussian")

    Returns:
        Adapter instance that handles this function

    Raises:
        ValueError: If function ID format is invalid or no adapter found
    """
    # Validate function ID format (must have at least prefix.module.function)
    if "." not in fn_id:
        raise ValueError(
            f"Invalid function ID format: '{fn_id}'. Expected format: 'prefix.module.function'"
        )

    # Extract adapter prefix
    # Handle base.xarray.* namespace -> route to xarray adapter
    if fn_id.startswith("base.xarray."):
        prefix = "xarray"
    else:
        # Extract adapter prefix (first part before first dot)
        prefix = fn_id.split(".", 1)[0]

    # Look up adapter in registry
    if prefix not in ADAPTER_REGISTRY:
        raise ValueError(f"No adapter found for prefix: '{prefix}'")

    return ADAPTER_REGISTRY[prefix]


# Reserved metadata keys that should never be treated as artifact inputs
METADATA_KEYS = {"reason", "_metadata", "_reason", "description"}


def _convert_inputs_to_artifacts(inputs: dict[str, Any]) -> list[Any]:
    """Convert input dict references to artifact objects.

    Args:
        inputs: Dictionary of input name to artifact reference dict

    Returns:
        List of (name, artifact) pairs for adapter consumption.

    Note:
        Filters out metadata keys like "reason" that are not artifact references.
        An artifact reference is a dict with ref_id, uri, path, or type keys.
    """
    result = []
    for name, value in inputs.items():
        # Skip reserved metadata keys
        if name in METADATA_KEYS:
            continue

        # Skip non-artifact values (plain strings that aren't valid artifact refs)
        if isinstance(value, str):
            # Plain strings should be artifact ref_ids - but "reason" descriptions
            # are also strings. We can identify real ref_ids by pattern:
            # - hex strings (UUID-like)
            # - file:// or mem:// URIs
            # If it looks like a sentence/description, skip it
            if " " in value or len(value) > 64:
                # Likely a description, not a ref_id
                continue
            # Otherwise treat as potential ref_id string
        elif isinstance(value, dict):
            # Validate it looks like an artifact reference
            if not any(k in value for k in ("ref_id", "uri", "path", "type")):
                # Not an artifact reference, skip
                continue
        elif isinstance(value, list):
            # Validate it's a list of potential artifact references
            # Items can be dicts (full refs) OR strings (ref_ids/URIs)
            valid_items = []
            for v in value:
                if isinstance(v, dict) and any(k in v for k in ("ref_id", "uri", "path", "type")):
                    valid_items.append(v)
                elif isinstance(v, str) and " " not in v and len(v) <= 64:
                    # String ref_id or URI - convert to minimal dict
                    valid_items.append({"ref_id": v})
                else:
                    # Invalid item, skip entire list
                    valid_items = []
                    break
            if not valid_items:
                # Support literal lists (e.g. data for histograms)
                result.append((name, value))
                continue
            value = valid_items  # Use normalized list
        else:
            # Other types (None, etc.) - skip
            continue

        result.append((name, value))

    return result


def _convert_outputs_to_refs(outputs: list[Any]) -> dict[str, dict[str, Any]]:
    """Convert output artifact objects to dict references.

    Args:
        outputs: List of output artifact dicts or objects

    Returns:
        Dictionary with 'outputs' key containing artifact references
    """
    if not outputs:
        return {"outputs": {}}

    output_dict = {}
    used_names = set()

    for i, artifact in enumerate(outputs):
        # If it's an object with to_ref method, call it
        if hasattr(artifact, "to_ref"):
            artifact = artifact.to_ref()

        # Try to get semantic name from output
        name = None

        # 1. Check metadata for explicit output_name
        if isinstance(artifact, dict):
            metadata = artifact.get("metadata", {})
            if isinstance(metadata, dict):
                name = metadata.get("output_name")

        # 2. Extract from path if available (e.g., "phasor_from_signal-mean.ome.tiff" -> "mean")
        if not name and isinstance(artifact, dict):
            path = artifact.get("path", "")
            if path:
                import re

                # Match pattern like "funcname-semanticname.ext"
                # Handle both .tiff and .ome.tiff by allowing multiple dots in extension
                match = re.search(r"-([a-zA-Z][a-zA-Z0-9_]*)\.[a-z.]+$", path)
                if match:
                    name = match.group(1)

        # 3. Fall back to indexed naming
        if not name or name in used_names:
            name = f"output_{i}" if i > 0 else "output"

        used_names.add(name)
        output_dict[name] = artifact

    return {"outputs": output_dict}


def dispatch_dynamic(
    fn_id: str,
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path | None = None,
    hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route dynamic function call to appropriate adapter for execution.

    Args:
        fn_id: Unique function identifier (e.g., "skimage.filters.gaussian")
        inputs: Dictionary of input name to artifact reference dict
        params: Parameter dictionary
        work_dir: Optional working directory for execution

    Returns:
        Dictionary with 'outputs' key containing artifact references

    Raises:
        ValueError: If function ID format is invalid or no adapter found
    """
    # Find the adapter for this function
    adapter = get_adapter_for_fn_id(fn_id)

    # Convert inputs from dict refs to artifacts (currently pass-through)
    input_artifacts = _convert_inputs_to_artifacts(inputs)

    # Execute via adapter
    # Check if adapter.execute supports hints parameter
    import inspect

    sig = inspect.signature(adapter.execute)
    exec_kwargs = {
        "fn_id": fn_id,
        "inputs": input_artifacts,
        "params": params,
    }
    if "work_dir" in sig.parameters:
        exec_kwargs["work_dir"] = work_dir
    if "hints" in sig.parameters:
        exec_kwargs["hints"] = hints

    output_artifacts = adapter.execute(**exec_kwargs)

    # Convert outputs from artifacts to dict refs
    result = _convert_outputs_to_refs(output_artifacts)

    return result
