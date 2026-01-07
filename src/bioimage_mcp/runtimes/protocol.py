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

            actual_type = ""

            # Input can be an artifact ref or a reference to previous step output
            if isinstance(input_value, dict):
                actual_type = str(input_value.get("type", "") or "")
            elif isinstance(input_value, str) and input_value in available_outputs:
                actual_type = available_outputs[input_value]

            # Check type compatibility
            if expected_types and actual_type:
                actual_types = actual_type if isinstance(actual_type, list) else [actual_type]
                # Cast to string for comparison
                actual_types = [str(t) for t in actual_types]

                # Check if all possible actual types are covered by expected types
                is_compatible = all(t in expected_types for t in actual_types)

                if not is_compatible:
                    actual_type_str = (
                        " | ".join(actual_types)
                        if isinstance(actual_type, list)
                        else str(actual_type)
                    )
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
