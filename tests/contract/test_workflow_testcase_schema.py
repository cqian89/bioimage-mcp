from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioimage_mcp.test_harness.models import (
    StepAssertion,
    StepContext,
    WorkflowStep,
    WorkflowTestCase,
)

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/007-workflow-test-harness/contracts/workflow-testcase.yaml"
)


def _load_contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text())


def test_workflow_testcase_schema_has_required_fields() -> None:
    contract = _load_contract()
    contract_required = set(contract["WorkflowTestCase"]["required"])

    schema = WorkflowTestCase.model_json_schema()
    schema_required = set(schema.get("required", []))

    assert schema_required == contract_required

    props = schema.get("properties", {})
    for field in contract_required:
        assert field in props


def test_workflow_step_schema_has_required_fields() -> None:
    contract = _load_contract()
    contract_required = set(contract["$defs"]["WorkflowStep"]["required"])

    schema = WorkflowStep.model_json_schema()
    schema_required = set(schema.get("required", []))

    assert schema_required == contract_required

    props = schema.get("properties", {})
    for field in contract_required:
        assert field in props


def test_step_assertion_validates_types() -> None:
    contract = _load_contract()
    contract_type_enum = set(contract["$defs"]["StepAssertion"]["properties"]["type"]["enum"])

    schema = StepAssertion.model_json_schema()
    schema_required = set(schema.get("required", []))

    assert schema_required == set(contract["$defs"]["StepAssertion"]["required"])

    schema_type_enum = set(schema["properties"]["type"].get("enum", []))
    assert schema_type_enum == contract_type_enum


def test_reference_syntax_parsing() -> None:
    context = StepContext(outputs={"fix_axes": {"ref_id": "ref-123", "type": "BioImageRef"}})

    resolved = context.resolve_reference("{fix_axes.output}")

    assert resolved == {"ref_id": "ref-123", "type": "BioImageRef"}
