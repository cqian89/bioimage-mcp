from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProtocolRequest:
    fn_id: str
    params: dict
    inputs: dict
    work_dir: str


@dataclass(frozen=True)
class ProtocolResponse:
    ok: bool
    outputs: dict
    log: str
    error: dict | None = None


@dataclass
class WorkflowPort:
    """Represents an input or output port in a workflow step."""

    name: str
    artifact_type: str | list[str]
    format: str | None = None


@dataclass
class WorkflowCompatibilityError:
    """Describes a workflow compatibility issue."""

    step_index: int
    port_name: str
    expected_type: str
    actual_type: str
    message: str


# Type inheritance map for compatibility checking (T018)
# Key: actual type, Value: list of types it satisfies
_TYPE_COMPATIBILITY = {
    "AxesRef": ["AxesRef", "ObjectRef", "ArtifactRef"],
    "FigureRef": ["FigureRef", "ObjectRef", "ArtifactRef"],
    "AxesImageRef": ["AxesImageRef", "ObjectRef", "ArtifactRef"],
    "GroupByRef": ["GroupByRef", "ObjectRef", "ArtifactRef"],
    "ObjectRef": ["ObjectRef", "ArtifactRef"],
    "BioImageRef": ["BioImageRef", "ArtifactRef"],
    "LabelImageRef": ["LabelImageRef", "BioImageRef", "ArtifactRef"],
    "TableRef": ["TableRef", "ArtifactRef"],
    "ScalarRef": ["ScalarRef", "ArtifactRef"],
    "PlotRef": ["PlotRef", "ArtifactRef"],
    "NativeOutputRef": ["NativeOutputRef", "ArtifactRef"],
    "LogRef": ["LogRef", "ArtifactRef"],
}


def _is_type_compatible(actual: str, expected: str) -> bool:
    """Check if actual artifact type is compatible with expected type."""
    if actual == expected or expected == "ArtifactRef" or not expected:
        return True
    return expected in _TYPE_COMPATIBILITY.get(actual, [])


def validate_workflow_compatibility(
    workflow_spec: dict[str, Any],
    function_ports: dict[str, dict[str, list[dict[str, Any]]]],
) -> list[WorkflowCompatibilityError]:
    """Validate workflow step I/O type compatibility.

    Checks that:
    1. Each step's inputs match the expected artifact types from the function definition
    2. Each step's outputs can be consumed by subsequent steps that reference them

    Args:
        workflow_spec: The workflow specification with steps
        function_ports: Mapping of fn_id -> {"inputs": [...], "outputs": [...]}
            Each port has: name, artifact_type, format (optional), required

    Returns:
        List of compatibility errors (empty if workflow is valid)
    """
    errors: list[WorkflowCompatibilityError] = []
    steps = workflow_spec.get("steps", [])

    # Track available outputs from previous steps
    available_outputs: dict[str, str | list[str]] = {}  # output_ref -> artifact_type

    for step_idx, step in enumerate(steps):
        fn_id = step.get("fn_id", "")
        step_inputs = step.get("inputs", {})

        # Get function port definitions
        fn_ports = function_ports.get(fn_id, {"inputs": [], "outputs": []})
        input_defs = {p.get("name"): p for p in fn_ports.get("inputs", [])}
        output_defs = {p.get("name"): p for p in fn_ports.get("outputs", [])}

        # print(f"DEBUG: fn_id={fn_id}, input_defs={input_defs}, step_inputs={step_inputs}")

        # Check for missing required inputs
        for input_name, input_def in input_defs.items():
            if input_def.get("required", False) and input_name not in step_inputs:
                msg = f"Step {step_idx} missing required input '{input_name}'"

                raw_type = input_def.get("artifact_type", "")
                if isinstance(raw_type, list):
                    expected_type_str = " | ".join(str(t) for t in raw_type)
                else:
                    expected_type_str = str(raw_type or "")

                errors.append(
                    WorkflowCompatibilityError(
                        step_index=step_idx,
                        port_name=str(input_name),
                        expected_type=expected_type_str,
                        actual_type="missing",
                        message=msg,
                    )
                )

        # Validate provided inputs
        for input_name, input_value in step_inputs.items():
            if input_name not in input_defs:
                continue  # Unknown input - might be optional

            raw_expected_type = input_defs[input_name].get("artifact_type", "")
            if isinstance(raw_expected_type, list):
                expected_types = [str(t) for t in raw_expected_type]
                expected_type_str = " | ".join(expected_types)
            else:
                expected_types = [str(raw_expected_type)] if raw_expected_type else []
                expected_type_str = str(raw_expected_type or "")

            actual_types = []

            # Input can be an artifact ref, a reference to previous step output,
            # or a list of either (T048)
            def _extract_types(val: Any) -> list[str]:
                if isinstance(val, list):
                    res = []
                    for item in val:
                        res.extend(_extract_types(item))
                    return res
                if isinstance(val, dict):
                    t = val.get("type", "")
                    return [str(t)] if t else []
                if isinstance(val, str) and val in available_outputs:
                    raw_avail = available_outputs[val]
                    if isinstance(raw_avail, list):
                        return [str(t) for t in raw_avail]
                    return [str(raw_avail)] if raw_avail else []
                return []

            actual_types = _extract_types(input_value)

            # Check type compatibility
            if expected_types and actual_types:
                # Check if all possible actual types are covered by expected types (T018: handle inheritance)
                is_compatible = True
                for act_t in actual_types:
                    if not any(_is_type_compatible(act_t, exp_t) for exp_t in expected_types):
                        is_compatible = False
                        break

                if not is_compatible:
                    actual_type_str = " | ".join(sorted(set(actual_types)))
                    msg = (
                        f"Step {step_idx} input '{input_name}': "
                        f"expected {expected_type_str}, got {actual_type_str}"
                    )
                    errors.append(
                        WorkflowCompatibilityError(
                            step_index=step_idx,
                            port_name=str(input_name),
                            expected_type=expected_type_str,
                            actual_type=actual_type_str,
                            message=msg,
                        )
                    )

        # Register this step's outputs as available
        for output_name, output_def in output_defs.items():
            output_ref = f"step{step_idx}.{output_name}"
            available_outputs[output_ref] = output_def.get("artifact_type", "") or ""

    return errors
