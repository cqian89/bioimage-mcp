"""Contract test that discovery listings remain summary-only (T000c2).

This test ensures that list_tools and search_functions responses do NOT
include params_schema blobs, maintaining the summary-first principle
per the constitution and meta-describe-protocol.md.
"""

from __future__ import annotations

import sqlite3

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def discovery_service():
    """Create a DiscoveryService with an in-memory database."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn, owns_conn=True)

    # Seed with sample tool and function data
    service.upsert_tool(
        tool_id="tools.sample",
        name="Sample Tool",
        description="A sample tool for testing",
        tool_version="1.0.0",
        env_id="bioimage-mcp-sample",
        manifest_path="/path/to/manifest.yaml",
        installed=True,
        available=True,
    )
    service.upsert_function(
        fn_id="sample.function",
        tool_id="tools.sample",
        name="Sample Function",
        description="A sample function",
        tags=["test", "sample"],
        inputs=[{"name": "input", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "LabelImageRef", "required": True}],
        params_schema={
            "type": "object",
            "properties": {
                "threshold": {"type": "number", "default": 0.5},
            },
        },
    )

    yield service
    service.close()


class TestListToolsSummaryOnly:
    """Tests that list_tools returns summary-only data."""

    def test_list_tools_no_params_schema(self, discovery_service: DiscoveryService) -> None:
        """Test that list_tools does not include params_schema."""
        result = discovery_service.list_tools(limit=10, cursor=None)

        for tool in result["items"]:
            # Should only have summary fields
            assert "name" in tool
            assert "full_path" in tool
            assert "type" in tool
            assert "has_children" in tool
            # Should NOT have detailed schema fields
            assert "params_schema" not in tool

    def test_list_tools_returns_minimal_fields(self, discovery_service: DiscoveryService) -> None:
        """Test that list_tools returns only the expected summary fields."""
        result = discovery_service.list_tools(limit=10, cursor=None)

        expected_fields = {"name", "full_path", "type", "has_children", "id", "summary", "children"}
        for tool in result["items"]:
            actual_fields = set(tool.keys())
            # We allow io field for function nodes
            if tool.get("type") == "function":
                expected_fields.add("io")

            # Check subset because some fields like io might be conditional or missing if empty
            assert actual_fields.issubset(expected_fields), (
                f"Unexpected fields in list_tools response: {actual_fields - expected_fields}"
            )
            assert "params_schema" not in actual_fields


class TestSearchFunctionsSummaryOnly:
    """Tests that search_functions returns summary-only data."""

    def test_search_functions_no_params_schema(self, discovery_service: DiscoveryService) -> None:
        """Test that search_functions does not include params_schema."""
        result = discovery_service.search_functions(
            keywords="sample",
            limit=10,
            cursor=None,
        )

        for fn in result["results"]:
            # Should only have summary fields
            assert "id" in fn
            assert "name" in fn
            assert "summary" in fn
            assert "tags" in fn
            assert "score" in fn
            assert "match_count" in fn
            # Should NOT have detailed schema fields
            assert "params_schema" not in fn
            assert "inputs" not in fn
            assert "outputs" not in fn

    def test_search_functions_returns_minimal_fields(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test that search_functions returns only the expected summary fields."""
        result = discovery_service.search_functions(
            keywords="sample",
            limit=10,
            cursor=None,
        )

        expected_fields = {
            "name",
            "tags",
            "score",
            "match_count",
            "id",
            "summary",
            "type",
            "io",
        }
        for fn in result["results"]:
            actual_fields = set(fn.keys())
            assert actual_fields.issubset(expected_fields), (
                f"Unexpected fields in search_functions response: {actual_fields - expected_fields}"
            )
            assert "params_schema" not in actual_fields


class TestDescribeFunctionHasSchema:
    """Tests that describe_function DOES include the full schema (on-demand)."""

    def test_describe_function_includes_schema(self, discovery_service: DiscoveryService) -> None:
        """Test that describe_function returns the params_schema (on-demand)."""
        result = discovery_service.describe_function("sample.function")

        # describe_function should include the schema
        assert "id" in result
        assert "params_schema" in result
        assert "properties" in result["params_schema"]
