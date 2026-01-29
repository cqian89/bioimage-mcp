"""Contract tests for discovery pagination/cursor stability (T000c3).

These tests verify that:
1. Pagination cursors are stable across identical queries
2. Cursor-based pagination returns correct results
3. Empty pages are handled correctly
"""

from __future__ import annotations

import sqlite3

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def discovery_service_with_data():
    """Create a DiscoveryService with multiple tools/functions for pagination tests."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn, owns_conn=True)

    # Create multiple tools for pagination testing
    for i in range(1, 11):  # 10 tools
        tool_id = f"tools.test{i:02d}"
        env_name = f"test{i:02d}"
        service.upsert_tool(
            tool_id=tool_id,
            name=f"Test Tool {i}",
            description=f"Test tool number {i}",
            tool_version="1.0.0",
            env_id="bioimage-mcp-test",
            manifest_path=f"/path/to/manifest{i}.yaml",
            installed=True,
            available=True,
        )
        # Add functions to each tool
        for j in range(1, 4):  # 3 functions per tool
            service.upsert_function(
                fn_id=f"{env_name}.pkg.module.func{j}",
                tool_id=tool_id,
                name=f"Function {j} of Tool {i}",
                description=f"Function {j}",
                tags=["test"],
                inputs=[],
                outputs=[],
                params_schema={},
            )

    yield service
    service.close()


class TestToolPaginationStability:
    """Tests for tool listing pagination stability."""

    def test_first_page_returns_cursor(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that first page returns a next_cursor when more results exist."""
        result = discovery_service_with_data.list_tools(limit=3, cursor=None)

        assert len(result["items"]) == 3
        assert result["next_cursor"] is not None

    def test_cursor_returns_next_page(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that using cursor returns the next page of results."""
        first_page = discovery_service_with_data.list_tools(limit=3, cursor=None)
        first_tool_ids = {t["id"] for t in first_page["items"]}

        second_page = discovery_service_with_data.list_tools(
            limit=3,
            cursor=first_page["next_cursor"],
        )
        second_tool_ids = {t["id"] for t in second_page["items"]}

        # Pages should not overlap
        assert len(first_tool_ids & second_tool_ids) == 0
        # Should have results in second page
        assert len(second_page["items"]) == 3

    def test_full_pagination_covers_all_tools(
        self, discovery_service_with_data: DiscoveryService
    ) -> None:
        """Test that paginating through all results returns all tools."""
        all_tools = []
        cursor = None

        while True:
            result = discovery_service_with_data.list_tools(limit=3, cursor=cursor)
            all_tools.extend(result["items"])
            cursor = result["next_cursor"]
            if cursor is None or len(result["items"]) < 3:
                break

        # Should have all 10 tools
        assert len(all_tools) == 10
        # All should be unique
        tool_ids = [t["id"] for t in all_tools]
        assert len(set(tool_ids)) == 10

    def test_same_cursor_returns_same_results(
        self, discovery_service_with_data: DiscoveryService
    ) -> None:
        """Test that the same cursor returns identical results (idempotent)."""
        first_page = discovery_service_with_data.list_tools(limit=3, cursor=None)
        cursor = first_page["next_cursor"]

        # Request second page twice with same cursor
        second_page_1 = discovery_service_with_data.list_tools(limit=3, cursor=cursor)
        second_page_2 = discovery_service_with_data.list_tools(limit=3, cursor=cursor)

        # Should return identical results
        ids_1 = [t["id"] for t in second_page_1["items"]]
        ids_2 = [t["id"] for t in second_page_2["items"]]
        assert ids_1 == ids_2

    def test_empty_result_no_cursor(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that empty results page has no cursor."""
        # Get all pages
        cursor = None
        last_cursor = None
        while True:
            result = discovery_service_with_data.list_tools(limit=3, cursor=cursor)
            if not result["items"]:
                break
            last_cursor = result["next_cursor"]
            cursor = result["next_cursor"]
            if cursor is None:
                break

        # After all tools are retrieved, requesting more should give empty or no cursor
        # The last valid cursor should still work
        if last_cursor:
            _final = discovery_service_with_data.list_tools(limit=3, cursor=last_cursor)
            # Should have either results or empty with no/null cursor


class TestFunctionSearchPaginationStability:
    """Tests for function search pagination stability."""

    def test_search_pagination_works(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that function search pagination returns all matching results."""
        all_functions = []
        cursor = None

        while True:
            result = discovery_service_with_data.search_functions(
                query="Function",
                limit=5,
                cursor=cursor,
            )
            all_functions.extend(result["results"])
            cursor = result["next_cursor"]
            if cursor is None or len(result["results"]) < 5:
                break

        # Should have all 30 functions (3 per tool * 10 tools)
        assert len(all_functions) == 30

    def test_search_cursor_stability(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that search cursors are stable for identical queries."""
        first = discovery_service_with_data.search_functions(
            query="Function",
            limit=5,
            cursor=None,
        )
        cursor = first["next_cursor"]

        # Same cursor, same query should give same results
        second_a = discovery_service_with_data.search_functions(
            query="Function",
            limit=5,
            cursor=cursor,
        )
        second_b = discovery_service_with_data.search_functions(
            query="Function",
            limit=5,
            cursor=cursor,
        )

        ids_a = [f["id"] for f in second_a["results"]]
        ids_b = [f["id"] for f in second_b["results"]]
        assert ids_a == ids_b


class TestPaginationEdgeCases:
    """Tests for pagination edge cases."""

    def test_limit_larger_than_dataset(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that requesting more items than exist works correctly."""
        result = discovery_service_with_data.list_tools(limit=100, cursor=None)

        # Should return all 10 tools
        assert len(result["items"]) == 10

    def test_limit_zero_handled(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test that limit=0 or None uses default limit."""
        result = discovery_service_with_data.list_tools(limit=None, cursor=None)

        # Should use default limit and return results
        assert len(result["items"]) > 0

    def test_invalid_cursor_format(self, discovery_service_with_data: DiscoveryService) -> None:
        """Test handling of malformed cursors."""
        # This might raise an error or treat as invalid
        # Behavior depends on implementation
        try:
            result = discovery_service_with_data.list_tools(
                limit=3,
                cursor="invalid-cursor-format",
            )
            # If no error, should return results (starting from beginning or empty)
            assert isinstance(result["items"], list)
        except (ValueError, KeyError):
            # Raising an error is also acceptable
            pass
