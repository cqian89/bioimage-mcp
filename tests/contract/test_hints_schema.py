from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.schemas import (
    ErrorHints,
    FunctionHints,
    InputRequirement,
    NextStepHint,
    OutputDescription,
    SuccessHints,
    SuggestedFix,
)
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.manifest_schema import FunctionResponse
from bioimage_mcp.registry.schema_cache import SchemaCache
from bioimage_mcp.storage.sqlite import init_schema

ALLOWED_ARTIFACT_TYPES = {
    "BioImageRef",
    "LabelImageRef",
    "TableRef",
    "LogRef",
    "NativeOutputRef",
    "PlotRef",
    "ObjectRef",
    "GroupByRef",
    "FigureRef",
    "AxesRef",
    "AxesImageRef",
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

    expected_axes_schema = props["expected_axes"]
    any_of = expected_axes_schema.get("anyOf", [])
    array_schema = next(
        (item for item in any_of if item.get("type") == "array"),
        expected_axes_schema if expected_axes_schema.get("type") == "array" else None,
    )
    assert array_schema is not None
    assert array_schema["items"]["pattern"] == "^[A-Z]$"

    supported_storage_schema = props["supported_storage_types"]
    any_of = supported_storage_schema.get("anyOf", [])
    array_schema = next(
        (item for item in any_of if item.get("type") == "array"),
        supported_storage_schema if supported_storage_schema.get("type") == "array" else None,
    )
    assert array_schema is not None
    assert set(array_schema["items"].get("enum", [])) == ALLOWED_STORAGE_TYPES


def test_output_description_schema() -> None:
    schema = OutputDescription.model_json_schema()

    assert set(schema.get("required", [])) == {"type", "description"}

    props = schema.get("properties", {})
    for field in ["type", "description"]:
        assert field in props

    assert set(props["type"].get("enum", [])) == ALLOWED_ARTIFACT_TYPES


def test_next_step_hint_schema() -> None:
    schema = NextStepHint.model_json_schema()

    assert set(schema.get("required", [])) == {"reason"}

    props = schema.get("properties", {})
    for field in ["id", "fn_id", "reason", "required_inputs"]:
        assert field in props

    required_inputs_schema = props["required_inputs"]
    any_of = required_inputs_schema.get("anyOf", [])
    array_schema = next(
        (item for item in any_of if item.get("type") == "array"),
        required_inputs_schema if required_inputs_schema.get("type") == "array" else None,
    )
    assert array_schema is not None
    assert array_schema["items"]["type"] == "string"


def test_suggested_fix_schema() -> None:
    schema = SuggestedFix.model_json_schema()

    assert set(schema.get("required", [])) == {"params", "explanation"}

    props = schema.get("properties", {})
    for field in ["id", "fn_id", "params", "explanation"]:
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


def test_describe_function_response_structure() -> None:
    """Validate describe_function response includes inputs and outputs with hints."""
    response = {
        "fn_id": "base.phasorpy.phasor.phasor_from_signal",
        "name": "Phasor transform",
        "description": "Convert FLIM dataset to phasor coordinates",
        "schema": {"type": "object", "properties": {}},
        "inputs": {
            "signal": {
                "type": "BioImageRef",
                "required": True,
                "description": "FLIM image data",
                "expected_axes": ["T", "Y", "X"],
                "preprocessing_hint": ("If T has only 1 sample, check if FLIM bins are in Z"),
            }
        },
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "description": "Mean intensity",
            },
            "output_1": {
                "type": "BioImageRef",
                "description": "Phasor G coordinates",
            },
        },
    }

    assert "fn_id" in response
    assert "inputs" in response
    assert "outputs" in response

    for input_requirement in response["inputs"].values():
        InputRequirement.model_validate(input_requirement)

    for output_description in response["outputs"].values():
        OutputDescription.model_validate(output_description)


def test_run_function_success_response_with_hints() -> None:
    """Validate run_function success response includes hints."""
    response = {
        "result": {
            "status": "succeeded",
            "outputs": {"output_1": {"ref_id": "abc123", "type": "BioImageRef"}},
            "hints": {
                "next_steps": [
                    {
                        "fn_id": "base.phasorpy.phasor.phasor_transform",
                        "reason": "Apply calibration using reference standard",
                    }
                ],
                "common_issues": ["Raw phasors are uncalibrated"],
            },
        },
        "workflow_hint": None,
    }

    assert response["result"]["status"] == "succeeded"
    assert "hints" in response["result"]
    SuccessHints.model_validate(response["result"]["hints"])


def test_run_function_error_response_with_hints() -> None:
    """Validate run_function error response includes diagnostic hints."""
    response = {
        "result": {
            "status": "failed",
            "error": {
                "message": "Not enough samples in axis T",
                "code": "AXIS_SAMPLES_ERROR",
            },
            "hints": {
                "diagnosis": "The T axis has only 1 sample",
                "suggested_fix": {
                    "fn_id": "base.xarray.rename",
                    "params": {"mapping": {"Z": "T", "T": "Z"}},
                    "explanation": "Swap Z and T axes",
                },
                "related_metadata": {
                    "detected_axes": "TCZYX",
                    "shape": [1, 1, 56, 512, 512],
                },
            },
        },
        "workflow_hint": None,
    }

    assert response["result"]["status"] == "failed"
    assert "hints" in response["result"]
    ErrorHints.model_validate(response["result"]["hints"])


def test_function_response_includes_inputs_outputs_hints() -> None:
    payload = {
        "fn_id": "sample.function",
        "schema": {"type": "object", "properties": {}},
        "inputs": {
            "image": {
                "type": "BioImageRef",
                "required": True,
                "description": "Input image",
            }
        },
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "description": "Output image",
            }
        },
        "hints": {
            "success_hints": {
                "next_steps": [
                    {
                        "fn_id": "sample.next",
                        "reason": "Continue processing",
                    }
                ]
            }
        },
    }

    model = FunctionResponse.model_validate(payload)
    dumped = model.model_dump(exclude_none=True, by_alias=True)
    assert "inputs" in dumped
    assert "outputs" in dumped
    assert "hints" in dumped


def test_describe_function_includes_manifest_hints_inputs_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_dir = tmp_path / "sample_tool"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "manifest.yaml"

    manifest_path.write_text(
        yaml.safe_dump(
            {
                "manifest_version": "0.0",
                "tool_id": "tools.sample",
                "tool_version": "0.1.0",
                "name": "Sample Tool",
                "description": "Sample tool",
                "env_id": "bioimage-mcp-sample",
                "entrypoint": "sample/entrypoint.py",
                "functions": [
                    {
                        "fn_id": "sample.function",
                        "tool_id": "tools.sample",
                        "name": "Sample Function",
                        "description": "Sample function",
                        "tags": ["sample"],
                        "inputs": [
                            {
                                "name": "image",
                                "artifact_type": "BioImageRef",
                                "required": True,
                                "description": "Input image",
                            }
                        ],
                        "outputs": [
                            {
                                "name": "output",
                                "artifact_type": "BioImageRef",
                                "required": True,
                                "description": "Output image",
                            }
                        ],
                        "params_schema": {"type": "object", "properties": {}},
                        "hints": {
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "required": True,
                                    "description": "Input image",
                                    "expected_axes": ["T", "Y", "X"],
                                    "preprocessing_hint": "Check axis order",
                                }
                            },
                            "outputs": {
                                "output": {
                                    "type": "BioImageRef",
                                    "description": "Output image",
                                }
                            },
                            "success_hints": {
                                "next_steps": [
                                    {
                                        "fn_id": "sample.next",
                                        "reason": "Continue processing",
                                    }
                                ]
                            },
                        },
                    }
                ],
            }
        )
    )

    cache_path = tmp_path / "schema_cache.json"
    cache = SchemaCache(cache_path)
    cache.set(
        tool_id="tools.sample",
        tool_version="0.1.0",
        fn_id="sample.function",
        params_schema={"type": "object", "properties": {}},
        introspection_source="manual",
    )

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[manifest_dir],
        schema_cache_path=cache_path,
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
    )
    monkeypatch.setattr(
        "bioimage_mcp.api.discovery.load_config",
        lambda: config,
    )

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.sample",
        name="Sample Tool",
        description="Sample tool",
        tool_version="0.1.0",
        env_id="bioimage-mcp-sample",
        manifest_path=str(manifest_path),
        available=True,
        installed=True,
    )
    service.upsert_function(
        fn_id="sample.function",
        tool_id="tools.sample",
        name="Sample Function",
        description="Sample function",
        tags=["sample"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {}},
    )

    described = service.describe_function("sample.function")
    assert described["inputs"]["image"]["description"] == "Input image"
    assert described["outputs"]["output"]["description"] == "Output image"
    assert described["hints"]["inputs"]["image"]["expected_axes"] == ["T", "Y", "X"]
    conn.close()
