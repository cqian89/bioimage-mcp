from __future__ import annotations

import logging
from typing import Any

import pytest

from bioimage_mcp.api.serializers import DescribeResponseSerializer


@pytest.fixture
def sample_describe_result() -> dict[str, Any]:
    """Sample successful describe result."""
    return {
        "id": "base.gauss",
        "type": "function",
        "name": "gaussian",
        "summary": "Apply Gaussian blur to an image.",
        "tags": ["filter", "blur"],
        "inputs": {
            "image": {
                "type": "BioImageRef",
                "required": True,
                "description": "Input image to blur.",
            }
        },
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "description": "Blurred image.",
            }
        },
        "params_schema": {
            "type": "object",
            "properties": {
                "sigma": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Standard deviation for Gaussian kernel.",
                },
                "truncate": {
                    "type": "number",
                    "default": 4.0,
                    "description": "Truncate the filter at this many standard deviations.",
                },
            },
            "required": ["sigma"],
        },
        "hints": {"success_hints": {"next_steps": ["Thresholding"]}},
    }


class TestDescribeResponseSerializer:
    """Unit tests for DescribeResponseSerializer."""

    def test_serialize_minimal(self, sample_describe_result: dict[str, Any]) -> None:
        """Test minimal verbosity for describe."""
        serializer = DescribeResponseSerializer()
        serialized = serializer.serialize(sample_describe_result, verbosity="minimal")

        # Core fields should be present
        assert serialized["id"] == "base.gauss"
        assert serialized["type"] == "function"
        assert serialized["summary"] == "Apply Gaussian blur to an image."
        assert "inputs" in serialized
        assert "outputs" in serialized
        assert "params_schema" in serialized

        # Non-core fields should be omitted
        assert "name" not in serialized
        assert "tags" not in serialized
        assert "hints" not in serialized

        # params_schema properties should not have descriptions
        properties = serialized["params_schema"]["properties"]
        assert "sigma" in properties
        assert "description" not in properties["sigma"]
        assert properties["sigma"]["type"] == "number"
        assert properties["sigma"]["default"] == 1.0

        assert "truncate" in properties
        assert "description" not in properties["truncate"]

        # Port descriptions should still be there
        assert serialized["inputs"]["image"]["description"] == "Input image to blur."
        assert serialized["outputs"]["output"]["description"] == "Blurred image."

    def test_serialize_standard(self, sample_describe_result: dict[str, Any]) -> None:
        """Test standard verbosity (full response)."""
        serializer = DescribeResponseSerializer()
        serialized = serializer.serialize(sample_describe_result, verbosity="standard")

        # Should be identical to input
        assert serialized == sample_describe_result
        assert "description" in serialized["params_schema"]["properties"]["sigma"]
        assert "hints" in serialized
        assert "name" in serialized

    def test_serialize_full(self, sample_describe_result: dict[str, Any]) -> None:
        """Test full verbosity (full response for now)."""
        serializer = DescribeResponseSerializer()
        serialized = serializer.serialize(sample_describe_result, verbosity="full")

        # Should be identical to input
        assert serialized == sample_describe_result

    def test_invalid_verbosity_coerced_to_minimal(
        self, sample_describe_result: dict[str, Any], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid verbosity is coerced to minimal with a warning."""
        serializer = DescribeResponseSerializer()
        with caplog.at_level(logging.WARNING):
            serialized = serializer.serialize(sample_describe_result, verbosity="invalid-level")

        assert "Invalid verbosity 'invalid-level', coercing to 'minimal'" in caplog.text
        # Should match minimal output
        assert "hints" not in serialized
        assert "description" not in serialized["params_schema"]["properties"]["sigma"]

    def test_batch_describe_serialization(self, sample_describe_result: dict[str, Any]) -> None:
        """Test serialization of batch describe results."""
        batch_result = {
            "schemas": {
                "base.gauss": sample_describe_result,
                "base.median": {
                    "id": "base.median",
                    "type": "function",
                    "summary": "Median filter",
                    "params_schema": {
                        "properties": {"size": {"type": "integer", "description": "Kernel size"}}
                    },
                },
            },
            "errors": {},
        }

        serializer = DescribeResponseSerializer()
        serialized = serializer.serialize(batch_result, verbosity="minimal")

        assert "schemas" in serialized
        assert "errors" in serialized

        gauss = serialized["schemas"]["base.gauss"]
        assert "hints" not in gauss
        assert "description" not in gauss["params_schema"]["properties"]["sigma"]

        median = serialized["schemas"]["base.median"]
        assert "description" not in median["params_schema"]["properties"]["size"]

    def test_single_error_response(self) -> None:
        """Test that single error responses are returned as is."""
        error_res = {"error": {"message": "Not found", "code": 404}}
        serializer = DescribeResponseSerializer()
        serialized = serializer.serialize(error_res, verbosity="minimal")
        assert serialized == error_res

    def test_non_function_node_minimal(self) -> None:
        """Test minimal serialization for non-function nodes."""
        node_res = {
            "id": "base",
            "type": "package",
            "name": "base",
            "summary": "Base tool pack",
            "children": [{"id": "base.preprocess", "type": "module"}],
        }
        serializer = DescribeResponseSerializer()
        serialized = serializer.serialize(node_res, verbosity="minimal")

        assert serialized["id"] == "base"
        assert serialized["type"] == "package"
        assert serialized["summary"] == "Base tool pack"
        # Since I am strictly following the core fields list, 'name' and 'children' are omitted
        assert "name" not in serialized
        assert "children" not in serialized
