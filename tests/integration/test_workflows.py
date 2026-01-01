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
            # Check if it's a mapping of name -> artifact ref
            for value in output.values():
                if isinstance(value, dict) and "type" in value:
                    assert value["type"] == expected_type
                    continue
                # It might be the workflow_record which has no type field
                # but we already filtered it out in _coerce_output_ref
                raise AssertionError(f"Output value {value} is not an artifact reference")
            return
    raise AssertionError(f"Output {output} is not an artifact reference")


@pytest.mark.mock_execution
@pytest.mark.timeout(10)
def test_full_discovery_to_execution_flow(mcp_test_client, sample_flim_image) -> None:
    search_results = mcp_test_client.search_functions("phasor FLIM")
    fn_ids = {fn["fn_id"] for fn in search_results["functions"]}
    assert "base.phasorpy.phasor.phasor_from_signal" in fn_ids

    mcp_test_client.activate_functions(
        [
            "base.xarray.rename",
            "base.phasorpy.phasor.phasor_from_signal",
        ]
    )

    schema = mcp_test_client.describe_function("base.xarray.rename")
    assert schema["fn_id"] == "base.xarray.rename"
    assert schema["schema"]["type"] == "object"

    relabeled = mcp_test_client.call_tool(
        fn_id="base.xarray.rename",
        inputs={"image": sample_flim_image},
        params={"mapping": {"Z": "T", "T": "Z"}},
    )
    relabeled_output = _coerce_output_ref(relabeled["outputs"])

    phasor = mcp_test_client.call_tool(
        fn_id="base.phasorpy.phasor.phasor_from_signal",
        inputs={"signal": relabeled_output},
        params={"harmonic": 1},
    )

    outputs = phasor["outputs"]
    assert "output" in outputs
    assert "output_1" in outputs
    assert "output_2" in outputs
    _assert_output_type(outputs["output"], "BioImageRef")
    _assert_output_type(outputs["output_1"], "BioImageRef")
    _assert_output_type(outputs["output_2"], "BioImageRef")


@pytest.mark.real_execution
@pytest.mark.timeout(60)
def test_flim_phasor_golden_path(mcp_test_client, sample_flim_image) -> None:
    sample_uri = sample_flim_image["uri"]
    sample_path = Path(sample_uri.replace("file://", ""))
    if not sample_path.exists():
        pytest.skip(f"Missing FLIM dataset at {sample_path}")

    mcp_test_client.activate_functions(
        [
            "base.xarray.transpose",
            "base.phasorpy.phasor.phasor_from_signal",
        ]
    )

    swapped = mcp_test_client.call_tool(
        fn_id="base.xarray.transpose",
        inputs={"image": sample_flim_image},
        params={"dims": ["Z", "C", "T", "Y", "X"]},
    )
    if "outputs" not in swapped:
        pytest.fail(f"Transpose failed: {swapped.get('error') or swapped}")
    swapped_output = _coerce_output_ref(swapped["outputs"])

    phasor = mcp_test_client.call_tool(
        fn_id="base.phasorpy.phasor.phasor_from_signal",
        inputs={"signal": swapped_output},
        params={"harmonic": 1, "axis": 0},
    )
    if "outputs" not in phasor:
        pytest.fail(f"Phasor failed: {phasor.get('error') or phasor}")
    outputs = phasor["outputs"]

    assert "mean" in outputs
    assert "real" in outputs
    assert "imag" in outputs
    _assert_output_type(outputs["mean"], "BioImageRef")
    _assert_output_type(outputs["real"], "BioImageRef")
    _assert_output_type(outputs["imag"], "BioImageRef")


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
