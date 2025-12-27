from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW_CASES_DIR = Path(__file__).parent / "workflow_cases"


def _load_workflow_cases() -> list[object]:
    case_files = sorted(WORKFLOW_CASES_DIR.glob("*.yaml"))
    cases: list[object] = []

    for case_path in case_files:
        data = yaml.safe_load(case_path.read_text())
        if data is None:
            continue
        if isinstance(data, list):
            for idx, case in enumerate(data):
                case_id = f"{case_path.name}::case-{idx}"
                cases.append(pytest.param(case_path, case, id=case_id))
            continue
        if isinstance(data, dict):
            cases.append(pytest.param(case_path, data, id=case_path.name))
            continue
        raise AssertionError(f"Workflow case file must be a mapping or list: {case_path}")

    if not cases:
        return [pytest.param(None, None, id="no-workflow-cases")]

    return cases


def _resolve_inputs(inputs: dict[str, Any], refs: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in inputs.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            ref_name = value[1:-1]
            resolved[key] = refs[ref_name]
        else:
            resolved[key] = value
    return resolved


def _coerce_output_ref(outputs: Any) -> Any:
    if isinstance(outputs, dict) and len(outputs) == 1:
        return next(iter(outputs.values()))
    return outputs


def _assert_output_type(output: Any, expected_type: str) -> None:
    if isinstance(output, dict) and "type" in output:
        assert output["type"] == expected_type
        return
    raise AssertionError("Output is not an artifact reference with a type field")


@pytest.mark.asyncio
@pytest.mark.mock_execution
async def test_full_discovery_to_execution_flow(mcp_test_client, sample_flim_image) -> None:
    search_results = await mcp_test_client.search_functions("phasor FLIM")
    fn_ids = {fn["fn_id"] for fn in search_results["functions"]}
    assert "base.phasor_from_flim" in fn_ids

    await mcp_test_client.activate_functions(["base.relabel_axes", "base.phasor_from_flim"])

    schema = await mcp_test_client.describe_function("base.relabel_axes")
    assert schema["fn_id"] == "base.relabel_axes"
    assert schema["schema"]["type"] == "object"

    relabeled = await mcp_test_client.call_tool(
        fn_id="base.relabel_axes",
        inputs={"image": sample_flim_image},
        params={"axis_mapping": {"Z": "T", "T": "Z"}},
    )
    relabeled_output = _coerce_output_ref(relabeled["outputs"])

    phasor = await mcp_test_client.call_tool(
        fn_id="base.phasor_from_flim",
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


@pytest.mark.asyncio
@pytest.mark.real_execution
async def test_flim_phasor_golden_path(mcp_test_client, sample_flim_image) -> None:
    await mcp_test_client.activate_functions(["base.relabel_axes", "base.phasor_from_flim"])

    relabeled = await mcp_test_client.call_tool(
        fn_id="base.relabel_axes",
        inputs={"image": sample_flim_image},
        params={"axis_mapping": {"Z": "T", "T": "Z"}},
    )
    relabeled_output = _coerce_output_ref(relabeled["outputs"])

    phasor = await mcp_test_client.call_tool(
        fn_id="base.phasor_from_flim",
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


@pytest.mark.asyncio
@pytest.mark.mock_execution
@pytest.mark.parametrize("case_path, case_data", _load_workflow_cases())
async def test_workflow_from_yaml(
    mcp_test_client, case_path: Path | None, case_data: dict[str, Any] | None
) -> None:
    if case_data is None:
        pytest.fail("No workflow YAML cases found")
    assert case_path is not None

    refs: dict[str, Any] = {}
    last_output: Any = None

    for step in case_data["steps"]:
        inputs = _resolve_inputs(step.get("inputs", {}), refs)
        params = step.get("params", {})
        result = await mcp_test_client.call_tool(
            fn_id=step["fn_id"],
            inputs=inputs,
            params=params,
        )
        outputs = result["outputs"]
        last_output = _coerce_output_ref(outputs)

        if "output_ref" in step:
            refs[step["output_ref"]] = last_output

    for assertion in case_data.get("assertions", []):
        if "artifact_exists" in assertion:
            ref_name = assertion["artifact_exists"]
            assert ref_name in refs
        if "output_type" in assertion:
            _assert_output_type(last_output, assertion["output_type"])
        if "metadata_contains" in assertion:
            metadata = last_output.get("metadata", {})
            for key, expected in assertion["metadata_contains"].items():
                assert metadata.get(key) == expected
