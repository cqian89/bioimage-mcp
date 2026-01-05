"""Contract tests for the 'list' MCP tool.

These tests verify the new API behavior with:
- Deterministic ordering with cursor pagination
- Child counts for non-leaf nodes
- I/O summaries for function nodes
- NOT_FOUND error for invalid paths
"""

import pytest
from bioimage_mcp.api.schemas import (
    ListRequest,
    ListResponse,
    CatalogNode,
    NodeType,
    ChildCounts,
    IOSummary,
)


# T032: Deterministic ordering + cursor pagination
def test_list_returns_deterministic_order_with_pagination():
    """List should return items in deterministic order with cursor/limit/next_cursor."""
    # Given: A catalog with multiple items
    # When: list(path=None, limit=2)
    # Then: Response has items, next_cursor for more results
    # And: Repeated calls with same cursor return same results
    pytest.skip("Not implemented - RED phase")


# T033: Child counts
def test_list_includes_child_counts_for_non_leaf_nodes():
    """Non-leaf nodes should include children.total and children.by_type."""
    # Given: An environment with packages
    # When: list(path=None, include_counts=True)
    # Then: Each non-leaf node has children.total > 0
    # And: children.by_type shows counts per NodeType
    pytest.skip("Not implemented - RED phase")


# T034: I/O summaries for functions
def test_list_includes_io_summaries_for_function_nodes():
    """Function nodes should include io.inputs and io.outputs summaries."""
    # Given: A module with functions
    # When: list(path="base.ops")
    # Then: Function nodes have io.inputs and io.outputs lists
    pytest.skip("Not implemented - RED phase")


# T035: NOT_FOUND error
def test_list_returns_not_found_for_invalid_path():
    """List should return NOT_FOUND error for non-existent paths."""
    # Given: An invalid path
    # When: list(path="invalid.nonexistent.path")
    # Then: Response contains error with code "NOT_FOUND"
    pytest.skip("Not implemented - RED phase")
