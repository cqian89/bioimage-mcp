"""Contract test for cellpose.segment meta.describe response format (T014a).

Validates that the meta.describe response for cellpose.segment includes
the required fields: ok, result, and tool_version.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, model_validator


class CellposeMetaDescribeResponse(BaseModel):
    """Expected schema for cellpose.segment meta.describe response."""

    ok: bool
    result: dict[str, Any] | None = None
    error: str | dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_response(self) -> CellposeMetaDescribeResponse:
        if self.ok:
            if self.result is None:
                raise ValueError("result is required when ok is True")
            if "params_schema" not in self.result:
                raise ValueError("result.params_schema is required")
            if "tool_version" not in self.result:
                raise ValueError("result.tool_version is required")
            if "introspection_source" not in self.result:
                raise ValueError("result.introspection_source is required")
        else:
            if self.error is None:
                raise ValueError("error is required when ok is False")
        return self


class TestCellposeMetaDescribeContract:
    """Contract tests for cellpose.segment meta.describe response."""

    def test_success_response_has_required_fields(self) -> None:
        """Test that success response includes ok, result, and tool_version."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "diameter": {"type": "number", "default": 30.0},
                    },
                    "required": [],
                },
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }

        validated = CellposeMetaDescribeResponse(**response)
        assert validated.ok is True
        assert validated.result is not None
        assert "tool_version" in validated.result
        assert validated.result["tool_version"] == "4.0.1"

    def test_success_response_requires_params_schema(self) -> None:
        """Test that params_schema is required in result."""
        response = {
            "ok": True,
            "result": {
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }

        with pytest.raises(ValueError, match="params_schema is required"):
            CellposeMetaDescribeResponse(**response)

    def test_success_response_requires_tool_version(self) -> None:
        """Test that tool_version is required in result."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {"type": "object"},
                "introspection_source": "python_api",
            },
        }

        with pytest.raises(ValueError, match="tool_version is required"):
            CellposeMetaDescribeResponse(**response)

    def test_success_response_requires_introspection_source(self) -> None:
        """Test that introspection_source is required in result."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {"type": "object"},
                "tool_version": "4.0.1",
            },
        }

        with pytest.raises(ValueError, match="introspection_source is required"):
            CellposeMetaDescribeResponse(**response)

    def test_error_response_has_required_fields(self) -> None:
        """Test that error response includes ok and error."""
        response = {
            "ok": False,
            "error": "Unknown function: cellpose.unknown",
        }

        validated = CellposeMetaDescribeResponse(**response)
        assert validated.ok is False
        assert validated.error is not None
        assert "Unknown function" in validated.error

    def test_error_response_requires_error_field(self) -> None:
        """Test that error field is required when ok is False."""
        response = {
            "ok": False,
        }

        with pytest.raises(ValueError, match="error is required when ok is False"):
            CellposeMetaDescribeResponse(**response)

    def test_tool_version_format(self) -> None:
        """Test that tool_version is a valid version string."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {"type": "object", "properties": {}, "required": []},
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }

        validated = CellposeMetaDescribeResponse(**response)
        version = validated.result["tool_version"]  # type: ignore

        # Version should be a non-empty string
        assert isinstance(version, str)
        assert len(version) > 0
        # If not "unknown", should have version-like format
        if version != "unknown":
            parts = version.split(".")
            assert len(parts) >= 1, "Version should have at least one part"

    def test_introspection_source_valid_values(self) -> None:
        """Test that introspection_source has valid value."""
        valid_sources = ["python_api", "argparse", "manual"]

        for source in valid_sources:
            response = {
                "ok": True,
                "result": {
                    "params_schema": {"type": "object", "properties": {}, "required": []},
                    "tool_version": "4.0.1",
                    "introspection_source": source,
                },
            }
            validated = CellposeMetaDescribeResponse(**response)
            assert validated.result["introspection_source"] == source  # type: ignore

    def test_params_schema_is_valid_json_schema(self) -> None:
        """Test that params_schema follows JSON Schema structure."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "diameter": {
                            "type": "number",
                            "default": 30.0,
                            "description": "Cell diameter in pixels",
                        },
                        "flow_threshold": {
                            "type": "number",
                            "default": 0.4,
                            "description": "Flow threshold",
                        },
                    },
                    "required": [],
                },
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }

        validated = CellposeMetaDescribeResponse(**response)
        schema = validated.result["params_schema"]  # type: ignore

        # Validate JSON Schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert isinstance(schema["required"], list)

    def test_cellpose_model_eval_describe_contract(self) -> None:
        """T049: Contract test for describe of CellposeModel.eval.

        Asserts ObjectRef input port and that artifact ports are NOT in params_schema.
        """
        from bioimage_mcp.artifacts.models import ARTIFACT_TYPES
        from bioimage_mcp.registry.manifest_schema import Function

        # Verify ObjectRef is a known artifact type
        assert "ObjectRef" in ARTIFACT_TYPES

        # This will likely fail if Function model doesn't support the new port structure or if

        # the function isn't yet correctly defined in the system.
        fn = Function(
            fn_id="cellpose.CellposeModel.eval",
            tool_id="bioimage-mcp-cellpose",
            name="eval",
            description="Run Cellpose segmentation",
            inputs=[
                {"name": "x", "artifact_type": "BioImageRef", "required": True},
                {"name": "model_ref", "artifact_type": "ObjectRef", "required": True},
            ],
            outputs=[{"name": "masks", "artifact_type": "LabelImageRef"}],
            params_schema={
                "type": "object",
                "properties": {
                    "channels": {"type": "array", "items": {"type": "integer"}},
                    "diameter": {"type": "number"},
                },
                "required": ["channels"],
            },
        )

        # Assertions
        input_names = [p.name for p in fn.inputs]
        assert "model_ref" in input_names

        model_ref_port = next(p for p in fn.inputs if p.name == "model_ref")
        assert model_ref_port.artifact_type == "ObjectRef"

        # Verify artifact ports NOT in params_schema
        assert "x" not in fn.params_schema["properties"]
        assert "model_ref" not in fn.params_schema["properties"]
        assert "masks" not in fn.params_schema["properties"]
