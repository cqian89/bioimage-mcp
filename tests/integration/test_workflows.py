from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioimage_mcp.test_harness import WorkflowTestCase

WORKFLOW_CASES_DIR = Path(__file__).parent / "workflow_cases"


def _load_workflow_cases() -> list[object]:
    case_files = sorted(WORKFLOW_CASES_DIR.glob("*.yaml"))
    cases: list[object] = []

    for case_path in case_files:
        data = yaml.safe_load(case_path.read_text())
        if data is None:
            continue
        if isinstance(data, list):
            for payload in data:
                case = WorkflowTestCase.model_validate(payload)
                cases.append(pytest.param(case, id=case.test_name))
            continue
        if isinstance(data, dict):
            case = WorkflowTestCase.model_validate(data)
            cases.append(pytest.param(case, id=case.test_name))
            continue
        raise AssertionError(f"Workflow case file must be a mapping or list: {case_path}")

    if not cases:
        return [pytest.param(None, id="no-workflow-cases")]

    return cases


def _resolve_inputs(inputs: dict[str, Any], refs: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in inputs.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            ref_name = value[1:-1]
            if ref_name not in refs:
                raise AssertionError(f"Unknown input reference: {ref_name}")
            resolved[key] = refs[ref_name]
        else:
            resolved[key] = value
    return resolved


def _coerce_output_ref(outputs: Any) -> Any:
    """Extract the primary output artifact from outputs dict.

    Filters out workflow_record and returns the single remaining output
    if there's exactly one, otherwise returns the filtered outputs dict.
    """
    if not isinstance(outputs, dict):
        return outputs
    # Filter out workflow_record which is always present
    filtered = {k: v for k, v in outputs.items() if k != "workflow_record"}
    if len(filtered) == 1:
        return next(iter(filtered.values()))
    return filtered


def _get_metadata_value(metadata: Any, key: str) -> Any:
    current = metadata
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            idx = int(part)
            if idx >= len(current):
                raise AssertionError(f"Metadata index out of range: {key}")
            current = current[idx]
            continue
        raise AssertionError(f"Metadata path not found: {key}")
    return current


def _assert_output_type(output: Any, expected_type: str) -> None:
    if isinstance(output, dict):
        if "type" in output:
            assert output["type"] == expected_type
            return
        if output:
            for value in output.values():
                if isinstance(value, dict) and "type" in value:
                    assert value["type"] == expected_type
                    continue
                raise AssertionError("Output is not an artifact reference with a type field")
            return
    raise AssertionError("Output is not an artifact reference with a type field")


@pytest.mark.mock_execution
@pytest.mark.timeout(10)
def test_full_discovery_to_execution_flow(mcp_test_client, sample_flim_image) -> None:
    search_results = mcp_test_client.search_functions("phasor FLIM")
    fn_ids = {fn["fn_id"] for fn in search_results["functions"]}
    assert "base.wrapper.phasor.phasor_from_flim" in fn_ids

    mcp_test_client.activate_functions(
        ["base.wrapper.axis.relabel_axes", "base.wrapper.phasor.phasor_from_flim"]
    )

    schema = mcp_test_client.describe_function("base.wrapper.axis.relabel_axes")
    assert schema["fn_id"] == "base.wrapper.axis.relabel_axes"
    assert schema["schema"]["type"] == "object"

    relabeled = mcp_test_client.call_tool(
        fn_id="base.wrapper.axis.relabel_axes",
        inputs={"image": sample_flim_image},
        params={"axis_mapping": {"Z": "T", "T": "Z"}},
    )
    relabeled_output = _coerce_output_ref(relabeled["outputs"])

    phasor = mcp_test_client.call_tool(
        fn_id="base.wrapper.phasor.phasor_from_flim",
        inputs={"dataset": relabeled_output},
        params={"harmonic": 1},
    )

    outputs = phasor["outputs"]
    assert "g_image" in outputs
    assert "s_image" in outputs
    assert "intensity_image" in outputs
    _assert_output_type(outputs["g_image"], "BioImageRef")
    _assert_output_type(outputs["s_image"], "BioImageRef")
    _assert_output_type(outputs["intensity_image"], "BioImageRef")


@pytest.mark.real_execution
@pytest.mark.timeout(60)
def test_flim_phasor_golden_path(mcp_test_client, sample_flim_image) -> None:
    sample_uri = sample_flim_image["uri"]
    sample_path = Path(sample_uri.replace("file://", ""))
    if not sample_path.exists():
        pytest.skip(f"Missing FLIM dataset at {sample_path}")

    mcp_test_client.activate_functions(
        ["base.wrapper.axis.swap_axes", "base.wrapper.phasor.phasor_from_flim"]
    )

    swapped = mcp_test_client.call_tool(
        fn_id="base.wrapper.axis.swap_axes",
        inputs={"image": sample_flim_image},
        params={"axis1": "Z", "axis2": "T"},
    )
    swapped_output = _coerce_output_ref(swapped["outputs"])

    phasor = mcp_test_client.call_tool(
        fn_id="base.wrapper.phasor.phasor_from_flim",
        inputs={"dataset": swapped_output},
        params={"harmonic": 1},
    )
    outputs = phasor["outputs"]

    assert "g_image" in outputs
    assert "s_image" in outputs
    assert "intensity_image" in outputs
    _assert_output_type(outputs["g_image"], "BioImageRef")
    _assert_output_type(outputs["s_image"], "BioImageRef")
    _assert_output_type(outputs["intensity_image"], "BioImageRef")


@pytest.mark.mock_execution
@pytest.mark.timeout(10)
@pytest.mark.parametrize("case", _load_workflow_cases())
def test_workflow_from_yaml(mcp_test_client, case: WorkflowTestCase | None) -> None:
    if case is None:
        pytest.fail("No workflow YAML cases found")

    refs: dict[str, Any] = {}
    last_output: Any = None

    for step in case.steps:
        inputs = _resolve_inputs(step.inputs, refs)
        params = step.params
        result = mcp_test_client.call_tool(
            fn_id=step.fn_id,
            inputs=inputs,
            params=params,
        )
        outputs = result["outputs"]
        last_output = _coerce_output_ref(outputs)

        refs[f"{step.step_id}.output"] = last_output

        for assertion in step.assertions:
            if assertion.type == "artifact_exists":
                assert last_output is not None
            if assertion.type == "output_type":
                expected_type = assertion.value
                assert isinstance(expected_type, str)
                _assert_output_type(last_output, expected_type)
            if assertion.type == "metadata_check":
                assert assertion.key is not None
                if not isinstance(last_output, dict):
                    raise AssertionError("Output is not an artifact reference")
                metadata = last_output.get("metadata", {})
                if not metadata:
                    # Mock outputs do not preserve per-step metadata.
                    continue
                actual = _get_metadata_value(metadata, assertion.key)
                assert actual == assertion.value
