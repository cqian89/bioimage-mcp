"""Contract tests for cellpose discovery and meta.describe response format.

Includes:
- T014a: cellpose.models.CellposeModel.eval meta.describe response format
- T049: describe of cellpose.models.CellposeModel.eval asserting ObjectRef input port
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest
from pydantic import BaseModel, model_validator

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema

# --- T014a: meta.describe Response Schema ---


class CellposeMetaDescribeResponse(BaseModel):
    """Expected schema for cellpose.models.CellposeModel.eval meta.describe response."""

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
            # callable_fingerprint is optional but allowed
        else:
            if self.error is None:
                raise ValueError("error is required when ok is False")
        return self


class TestCellposeMetaDescribeContract:
    """Contract tests for cellpose.models.CellposeModel.eval meta.describe response (T014a)."""

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


# --- T049: DiscoveryService Describe ObjectRef ---


class TestCellposeDescribeObjectRef:
    """T049: Contract tests for describe of cellpose.models.CellposeModel.eval with ObjectRef."""

    @pytest.fixture
    def discovery_service(self):
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        service = DiscoveryService(conn)

        # Setup tool and function
        service.upsert_tool(
            tool_id="tools.cellpose",
            name="Cellpose",
            description="Cellpose",
            tool_version="0.1.0",
            env_id="bioimage-mcp-cellpose",
            manifest_path="/abs/cellpose.yaml",
            available=True,
            installed=True,
        )

        # Define inputs as they would appear in the manifest
        inputs = [
            {"name": "model", "artifact_type": "ObjectRef", "required": True},
            {"name": "x", "artifact_type": "BioImageRef", "required": True},
        ]
        outputs = [{"name": "labels", "artifact_type": "LabelImageRef"}]

        service.upsert_function(
            id="cellpose.models.CellposeModel.eval",
            tool_id="tools.cellpose",
            name="Evaluate Cellpose Model",
            description="Run evaluation on a pre-initialized CellposeModel.",
            tags=["segmentation", "deep-learning"],
            inputs=inputs,
            outputs=outputs,
            params_schema={
                "type": "object",
                "properties": {
                    "channels": {"type": "array", "items": {"type": "integer"}},
                    "diameter": {"type": "number"},
                    "model": {
                        "type": "object",
                        "title": "ObjectRef",
                    },  # Should be filtered out by name
                    "x": {
                        "type": "object",
                        "title": "BioImageRef",
                    },  # Should be filtered out by name
                    "extra_object": {"type": "ObjectRef"},  # Should be filtered out by type (T049)
                },
                "required": ["channels", "model", "x"],
            },
        )
        yield service
        conn.close()

    def test_describe_cellpose_model_eval_has_objectref_input(self, discovery_service):
        """T049: Test that cellpose.models.CellposeModel.eval has ObjectRef input port."""
        described = discovery_service.describe_function(id="cellpose.models.CellposeModel.eval")

        assert "inputs" in described
        assert "model" in described["inputs"]
        assert described["inputs"]["model"]["type"] == "ObjectRef"
        assert "x" in described["inputs"]
        assert described["inputs"]["x"]["type"] == "BioImageRef"

        # Check new meta block (Task 1)
        assert "meta" in described
        assert described["meta"]["tool_version"] == "0.1.0"
        assert described["meta"]["introspection_source"] == "manual"
        assert "module" in described["meta"]
        # callable_fingerprint might be None if not cached/introspected
        assert "callable_fingerprint" in described["meta"]

    def test_describe_objectref_not_in_params_schema(self, discovery_service):
        """T049: Test that ObjectRef and other artifact ports are NOT in params_schema."""
        described = discovery_service.describe_function(id="cellpose.models.CellposeModel.eval")

        assert "params_schema" in described
        properties = described["params_schema"].get("properties", {})

        # Should be present
        assert "channels" in properties
        assert "diameter" in properties

        # Should be filtered out by name (as they are inputs)
        assert "model" not in properties
        assert "x" not in properties

        # Should be filtered out by type (ObjectRef)
        assert "extra_object" not in properties

        if "required" in described["params_schema"]:
            required = described["params_schema"]["required"]
            assert "model" not in required
            assert "x" not in required
            assert "channels" in required
