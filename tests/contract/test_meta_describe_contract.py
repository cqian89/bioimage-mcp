"""Contract tests for meta.describe request/response schema (T000c).

These tests validate the meta.describe protocol contract as specified
in specs/001-cellpose-pipeline/meta-describe-protocol.md.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import AliasChoices, BaseModel, Field, model_validator


class MetaDescribeRequest(BaseModel):
    """Expected schema for meta.describe request."""

    id: str = Field(
        default="meta.describe",
        validation_alias=AliasChoices("id", "fn_id"),
        serialization_alias="id",
    )
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_request(self) -> MetaDescribeRequest:
        if self.id != "meta.describe":
            raise ValueError("id must be 'meta.describe'")
        if "target_fn" not in self.params:
            raise ValueError("params.target_fn is required")
        return self


class MetaDescribeSuccessResponse(BaseModel):
    """Expected schema for meta.describe success response."""

    ok: bool = True
    result: dict[str, Any]

    @model_validator(mode="after")
    def _validate_response(self) -> MetaDescribeSuccessResponse:
        if not self.ok:
            raise ValueError("ok must be True for success response")
        # Validate result structure
        if "params_schema" not in self.result:
            raise ValueError("result.params_schema is required")
        if "tool_version" not in self.result:
            raise ValueError("result.tool_version is required")
        if "introspection_source" not in self.result:
            raise ValueError("result.introspection_source is required")
        return self


class MetaDescribeErrorResponse(BaseModel):
    """Expected schema for meta.describe error response."""

    ok: bool = False
    error: str

    @model_validator(mode="after")
    def _validate_error(self) -> MetaDescribeErrorResponse:
        if self.ok:
            raise ValueError("ok must be False for error response")
        return self


class TestMetaDescribeRequestContract:
    """Contract tests for meta.describe request schema."""

    def test_valid_request_accepted(self) -> None:
        """Test that a valid request passes validation."""
        request = {
            "id": "meta.describe",
            "params": {"target_fn": "cellpose.models.CellposeModel.eval"},
        }
        validated = MetaDescribeRequest(**request)
        assert validated.id == "meta.describe"
        assert validated.params["target_fn"] == "cellpose.models.CellposeModel.eval"

    def test_request_requires_id_meta_describe(self) -> None:
        """Test that id must be 'meta.describe'."""
        with pytest.raises(ValueError, match="id must be 'meta.describe'"):
            # This is tricky because the model_validator checks id == "meta.describe"
            # but we want to test what happens if it's NOT that.
            # The original test passed "other.function" which is correct for testing failure.
            request_fail = {
                "id": "other.function",
                "params": {"target_fn": "cellpose.models.CellposeModel.eval"},
            }
            MetaDescribeRequest(**request_fail)

    def test_request_requires_target_fn_param(self) -> None:
        """Test that params.target_fn is required."""
        request = {
            "id": "meta.describe",
            "params": {},
        }
        with pytest.raises(ValueError, match="params.target_fn is required"):
            MetaDescribeRequest(**request)


class TestMetaDescribeResponseContract:
    """Contract tests for meta.describe response schema."""

    def test_valid_success_response_accepted(self) -> None:
        """Test that a valid success response passes validation."""
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
        validated = MetaDescribeSuccessResponse(**response)
        assert validated.ok is True
        assert "params_schema" in validated.result

    def test_success_response_requires_params_schema(self) -> None:
        """Test that result.params_schema is required."""
        response = {
            "ok": True,
            "result": {
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }
        with pytest.raises(ValueError, match="params_schema is required"):
            MetaDescribeSuccessResponse(**response)

    def test_success_response_requires_tool_version(self) -> None:
        """Test that result.tool_version is required."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {"type": "object"},
                "introspection_source": "python_api",
            },
        }
        with pytest.raises(ValueError, match="tool_version is required"):
            MetaDescribeSuccessResponse(**response)

    def test_success_response_requires_introspection_source(self) -> None:
        """Test that result.introspection_source is required."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {"type": "object"},
                "tool_version": "4.0.1",
            },
        }
        with pytest.raises(ValueError, match="introspection_source is required"):
            MetaDescribeSuccessResponse(**response)

    def test_valid_error_response_accepted(self) -> None:
        """Test that a valid error response passes validation."""
        response = {
            "ok": False,
            "error": "Unknown function: cellpose.unknown",
        }
        validated = MetaDescribeErrorResponse(**response)
        assert validated.ok is False
        assert "Unknown function" in validated.error

    def test_introspection_source_values(self) -> None:
        """Test that valid introspection_source values are accepted."""
        valid_sources = ["python_api", "argparse", "manual"]

        for source in valid_sources:
            response = {
                "ok": True,
                "result": {
                    "params_schema": {"type": "object"},
                    "tool_version": "1.0.0",
                    "introspection_source": source,
                },
            }
            validated = MetaDescribeSuccessResponse(**response)
            assert validated.result["introspection_source"] == source


class TestMetaDescribeParamsSchemaContract:
    """Contract tests for the params_schema field structure."""

    def test_params_schema_is_json_schema_object(self) -> None:
        """Test that params_schema follows JSON Schema object format."""
        schema = {
            "type": "object",
            "properties": {
                "diameter": {
                    "type": "number",
                    "default": 30.0,
                    "description": "Cell diameter in pixels",
                },
            },
            "required": [],
        }

        # Should be valid JSON Schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert isinstance(schema["required"], list)

    def test_params_schema_property_has_description(self) -> None:
        """Test that each property should have a description."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "diameter": {
                            "type": "number",
                            "description": "Cell diameter in pixels",
                        },
                    },
                    "required": [],
                },
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }
        validated = MetaDescribeSuccessResponse(**response)
        props = validated.result["params_schema"]["properties"]
        for prop_name, prop_def in props.items():
            # Every property should have a description
            assert "description" in prop_def, f"Property {prop_name} missing description"
