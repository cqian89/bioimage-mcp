from __future__ import annotations

import pytest
from typing import Any

EXPECTED_IO_FUNCTIONS = {
    "base.io.bioimage.load",
    "base.io.bioimage.inspect",
    "base.io.bioimage.slice",
    "base.io.bioimage.validate",
    "base.io.bioimage.get_supported_formats",
    "base.io.bioimage.export",
}

DEPRECATED_FUNCTIONS = {
    "base.bioio.export",
}


def test_io_function_discovery(mcp_test_client):
    """
    T049: Verify all 6 I/O functions are discoverable and deprecated one is absent.
    """
    # 1. Check list_tools/search_functions for presence of expected functions
    search_result = mcp_test_client.search_functions("base.io.bioimage")
    found_fns = {fn["fn_id"] for fn in search_result.get("functions", [])}

    missing = EXPECTED_IO_FUNCTIONS - found_fns
    assert not missing, f"Missing expected I/O functions: {missing}"

    # 2. Verify deprecated functions are NOT in discovery
    found_deprecated = DEPRECATED_FUNCTIONS & found_fns
    assert not found_deprecated, f"Found deprecated functions: {found_deprecated}"

    # 3. Double check base.bioio.export specifically isn't there in a broader search
    all_tools = mcp_test_client.list_tools(flatten=True)
    all_fn_ids = {fn["fn_id"] for fn in all_tools.get("functions", [])}
    assert "base.bioio.export" not in all_fn_ids, (
        "base.bioio.export should be removed/deprecated from discovery"
    )

    # 4. Verify describe_function returns valid schema for each
    for fn_id in EXPECTED_IO_FUNCTIONS:
        desc = mcp_test_client.describe_function(fn_id)
        assert desc, f"Could not describe function {fn_id}"
        assert "fn_id" in desc
        assert desc["fn_id"] == fn_id
        assert "params_schema" in desc
        assert isinstance(desc["params_schema"], dict)


@pytest.mark.skip(reason="T046-T048 to be implemented later")
def test_io_workflow_e2e(mcp_test_client):
    """Placeholder for future E2E tests."""
    pass
