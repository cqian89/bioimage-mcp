"""Contract tests for StarDist discovery and meta.describe response format."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest
from pydantic import BaseModel, model_validator

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


class StarDistMetaDescribeResponse(BaseModel):
    """Expected schema for StarDist meta.describe response."""

    ok: bool
    result: dict[str, Any] | None = None
    error: str | dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_response(self) -> StarDistMetaDescribeResponse:
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


class TestStarDistMetaDescribeContract:
    """Contract tests for StarDist meta.describe response."""

    def test_success_response_has_required_fields(self) -> None:
        """Test that success response includes ok, result, and tool_version."""
        response = {
            "ok": True,
            "result": {
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "prob_thresh": {"type": "number"},
                    },
                    "required": [],
                },
                "tool_version": "0.9.2",
                "introspection_source": "python_api",
            },
        }

        validated = StarDistMetaDescribeResponse(**response)
        assert validated.ok is True
        assert validated.result is not None
        assert "tool_version" in validated.result
        assert validated.result["tool_version"] == "0.9.2"


class TestStarDistDescribeArtifactFiltering:
    """Contract tests for describe of StarDist callables with artifact filtering."""

    @pytest.fixture
    def discovery_service(self):
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        service = DiscoveryService(conn)

        # Setup tool and function
        service.upsert_tool(
            tool_id="tools.stardist",
            name="StarDist",
            description="StarDist",
            tool_version="0.1.0",
            env_id="bioimage-mcp-stardist",
            manifest_path="/abs/stardist.yaml",
            available=True,
            installed=True,
        )

        # Define inputs as they would appear in the manifest
        inputs = [
            {"name": "model", "artifact_type": "ObjectRef", "required": True},
            {"name": "image", "artifact_type": "BioImageRef", "required": True},
        ]
        outputs = [
            {"name": "labels", "artifact_type": "LabelImageRef"},
            {"name": "details", "artifact_type": "NativeOutputRef"},
        ]

        service.upsert_function(
            id="stardist.models.StarDist2D.predict_instances",
            tool_id="tools.stardist",
            name="Predict Instances",
            description="Run StarDist prediction.",
            tags=["segmentation", "deep-learning"],
            inputs=inputs,
            outputs=outputs,
            params_schema={
                "type": "object",
                "properties": {
                    "prob_thresh": {"type": "number"},
                    "model": {
                        "type": "object",
                        "title": "ObjectRef",
                    },  # Should be filtered out by name/type
                    "image": {
                        "type": "object",
                        "title": "BioImageRef",
                    },  # Should be filtered out by name/type
                },
                "required": ["model", "image"],
            },
        )
        yield service
        conn.close()

    def test_describe_predict_instances_filters_artifacts(self, discovery_service):
        """Test that ObjectRef and BioImageRef ports are NOT in params_schema."""
        described = discovery_service.describe_function(
            id="stardist.models.StarDist2D.predict_instances"
        )

        assert "params_schema" in described
        properties = described["params_schema"].get("properties", {})

        # Should be present
        assert "prob_thresh" in properties

        # Should be filtered out
        assert "model" not in properties
        assert "image" not in properties

        if "required" in described["params_schema"]:
            required = described["params_schema"]["required"]
            assert "model" not in required
            assert "image" not in required
