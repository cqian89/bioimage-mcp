"""
Dynamic dispatch router for base tool pack.

Routes dynamic function calls (e.g., phasorpy.phasor.phasor_from_signal) to appropriate
adapters for execution. Handles artifact reference conversion between MCP
protocol (dict refs) and internal Artifact objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

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

    # Extract adapter prefix (first part before first dot)
    prefix = fn_id.split(".", 1)[0]

    # Look up adapter in registry
    if prefix not in ADAPTER_REGISTRY:
        raise ValueError(f"No adapter found for prefix: '{prefix}'")

    return ADAPTER_REGISTRY[prefix]


def _convert_inputs_to_artifacts(inputs: Dict[str, Any]) -> list[Any]:
    """Convert input dict references to artifact objects.

    Args:
        inputs: Dictionary of input name to artifact reference dict

    Returns:
        List of artifact reference dicts (pass-through for now)

    Note:
        For now, this is a pass-through that returns the input dict values.
        Full artifact resolution will be implemented when artifact store is available.
    """
    # TODO: Convert dict refs to actual Artifact objects when artifact store is integrated
    # For now, adapters are expected to handle dict refs directly
    return list(inputs.values())


def _convert_outputs_to_refs(outputs: list[Any]) -> Dict[str, Dict[str, Any]]:
    """Convert output artifact objects to dict references.

    Args:
        outputs: List of output artifact dicts or objects

    Returns:
        Dictionary with 'outputs' key containing artifact references
    """
    if not outputs:
        return {"outputs": {}}

    # For single output, use "output" key
    # TODO: Handle multiple outputs with proper naming
    if len(outputs) == 1:
        output_ref = outputs[0]
        # If it's an object with to_ref method, call it
        if hasattr(output_ref, "to_ref"):
            output_ref = output_ref.to_ref()
        return {"outputs": {"output": output_ref}}

    # Multiple outputs - use indexed names or adapter-specific names
    output_dict = {}
    for i, artifact in enumerate(outputs):
        key = f"output_{i}" if i > 0 else "output"
        # If it's an object with to_ref method, call it
        if hasattr(artifact, "to_ref"):
            output_dict[key] = artifact.to_ref()
        else:
            output_dict[key] = artifact

    return {"outputs": output_dict}


def dispatch_dynamic(
    fn_id: str,
    inputs: Dict[str, Any],
    params: Dict[str, Any],
    work_dir: Path | None = None,
) -> Dict[str, Any]:
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
    # Check if adapter.execute supports work_dir parameter
    import inspect

    sig = inspect.signature(adapter.execute)
    if "work_dir" in sig.parameters:
        output_artifacts = adapter.execute(
            fn_id=fn_id,
            inputs=input_artifacts,
            params=params,
            work_dir=work_dir,
        )
    else:
        output_artifacts = adapter.execute(
            fn_id=fn_id,
            inputs=input_artifacts,
            params=params,
        )

    # Convert outputs from artifacts to dict refs
    result = _convert_outputs_to_refs(output_artifacts)

    return result
