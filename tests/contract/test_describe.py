"""Contract tests for the 'describe' MCP tool.

These tests verify:
- Separated inputs/outputs/params_schema for functions
- Describe works for non-function nodes
- NOT_FOUND error for invalid IDs
"""

import pytest
from bioimage_mcp.api.schemas import (
    DescribeRequest,
    FunctionDescriptor,
    CatalogNode,
    InputPort,
    OutputPort,
)


# T036: Separated inputs/outputs/params_schema
def test_describe_function_separates_inputs_outputs_params():
    """Describe should return inputs, outputs, and params_schema as separate fields."""
    # Given: A valid function ID
    # When: describe(id="base.ops.gaussian")
    # Then: Response has inputs dict, outputs dict, params_schema dict
    # And: params_schema contains no artifact port keys
    pytest.skip("Not implemented - RED phase")


# T037: Describe non-function node
def test_describe_non_function_node_returns_catalog_node():
    """Describe on non-function should return CatalogNode with child preview."""
    # Given: A module ID (not a function)
    # When: describe(id="base.ops")
    # Then: Response is CatalogNode type with children info
    pytest.skip("Not implemented - RED phase")


# T038: NOT_FOUND error
def test_describe_returns_not_found_for_invalid_id():
    """Describe should return NOT_FOUND error for non-existent IDs."""
    # Given: An invalid function ID
    # When: describe(id="invalid.function.id")
    # Then: Response contains error with code "NOT_FOUND"
    pytest.skip("Not implemented - RED phase")
