from __future__ import annotations

from bioimage_mcp.api.schemas import (
    ErrorHints,
    FunctionHints,
    InputRequirement,
    NextStepHint,
    OutputDescription,
    SuccessHints,
    SuggestedFix,
)

ALLOWED_ARTIFACT_TYPES = {
    "BioImageRef",
    "LabelImageRef",
    "TableRef",
    "LogRef",
    "NativeOutputRef",
}
ALLOWED_STORAGE_TYPES = {"file", "zarr-temp"}


def test_input_requirement_schema() -> None:
    schema = InputRequirement.model_json_schema()

    assert set(schema.get("required", [])) == {"type", "required", "description"}

    props = schema.get("properties", {})
    for field in [
        "type",
        "required",
        "description",
        "expected_axes",
        "preprocessing_hint",
        "supported_storage_types",
    ]:
        assert field in props

    assert set(props["type"].get("enum", [])) == ALLOWED_ARTIFACT_TYPES
    assert props["expected_axes"]["items"]["pattern"] == "^[A-Z]$"
    assert set(props["supported_storage_types"]["items"].get("enum", [])) == ALLOWED_STORAGE_TYPES


def test_output_description_schema() -> None:
    schema = OutputDescription.model_json_schema()

    assert set(schema.get("required", [])) == {"type", "description"}

    props = schema.get("properties", {})
    for field in ["type", "description"]:
        assert field in props

    assert set(props["type"].get("enum", [])) == ALLOWED_ARTIFACT_TYPES


def test_next_step_hint_schema() -> None:
    schema = NextStepHint.model_json_schema()

    assert set(schema.get("required", [])) == {"fn_id", "reason"}

    props = schema.get("properties", {})
    for field in ["fn_id", "reason", "required_inputs"]:
        assert field in props

    assert props["required_inputs"]["items"]["type"] == "string"


def test_suggested_fix_schema() -> None:
    schema = SuggestedFix.model_json_schema()

    assert set(schema.get("required", [])) == {"fn_id", "params", "explanation"}

    props = schema.get("properties", {})
    for field in ["fn_id", "params", "explanation"]:
        assert field in props

    assert props["params"]["type"] == "object"


def test_success_hints_schema() -> None:
    schema = SuccessHints.model_json_schema()

    props = schema.get("properties", {})
    for field in ["next_steps", "common_issues"]:
        assert field in props

    assert "items" in props["next_steps"]
    assert props["common_issues"]["items"]["type"] == "string"


def test_error_hints_schema() -> None:
    schema = ErrorHints.model_json_schema()

    props = schema.get("properties", {})
    for field in ["diagnosis", "suggested_fix", "related_metadata"]:
        assert field in props


def test_function_hints_schema() -> None:
    schema = FunctionHints.model_json_schema()

    props = schema.get("properties", {})
    for field in ["inputs", "outputs", "success_hints", "error_hints"]:
        assert field in props

    assert "$ref" in props["inputs"]["additionalProperties"]
    assert "$ref" in props["outputs"]["additionalProperties"]
    assert "$ref" in props["error_hints"]["additionalProperties"]
