from __future__ import annotations


def test_pandas_allowlists_exist():
    """Verify that the pandas allowlists module and its expected constants exist."""
    # This is expected to fail initially (TDD Red phase)
    from bioimage_mcp.registry.dynamic import pandas_allowlists

    assert hasattr(pandas_allowlists, "PANDAS_DATAFRAME_CLASS")
    assert hasattr(pandas_allowlists, "PANDAS_DATAFRAME_METHODS")
    assert hasattr(pandas_allowlists, "PANDAS_GROUPBY_METHODS")
    assert hasattr(pandas_allowlists, "PANDAS_TOPLEVEL_FUNCTIONS")
    assert hasattr(pandas_allowlists, "PANDAS_DENYLIST")


def test_pandas_allowlist_discovery_count():
    """Verify that at least 50 functions are defined across all allowlist categories."""
    from bioimage_mcp.registry.dynamic.pandas_allowlists import (
        PANDAS_DATAFRAME_METHODS,
        PANDAS_GROUPBY_METHODS,
        PANDAS_TOPLEVEL_FUNCTIONS,
    )

    total_count = (
        len(PANDAS_DATAFRAME_METHODS) + len(PANDAS_GROUPBY_METHODS) + len(PANDAS_TOPLEVEL_FUNCTIONS)
    )
    assert total_count >= 50, f"Expected at least 50 functions, found {total_count}"


def test_pandas_denylist_integrity():
    """Verify that dangerous methods are denylisted and not present in any allowlist."""
    from bioimage_mcp.registry.dynamic.pandas_allowlists import (
        PANDAS_DATAFRAME_METHODS,
        PANDAS_DENYLIST,
        PANDAS_GROUPBY_METHODS,
        PANDAS_TOPLEVEL_FUNCTIONS,
    )

    # Required dangerous methods to block
    dangerous = {
        "eval",
        "to_pickle",
        "read_csv",
        "to_csv",
        "to_sql",
        "to_json",
        "to_html",
        "to_feather",
        "to_parquet",
    }

    for method in dangerous:
        assert method in PANDAS_DENYLIST, f"Method '{method}' should be in PANDAS_DENYLIST"

    # Ensure no denylisted method accidentally made it into an allowlist
    for method in PANDAS_DENYLIST:
        assert method not in PANDAS_DATAFRAME_METHODS, (
            f"Denylisted method '{method}' found in PANDAS_DATAFRAME_METHODS"
        )
        assert method not in PANDAS_GROUPBY_METHODS, (
            f"Denylisted method '{method}' found in PANDAS_GROUPBY_METHODS"
        )
        assert method not in PANDAS_TOPLEVEL_FUNCTIONS, (
            f"Denylisted method '{method}' found in PANDAS_TOPLEVEL_FUNCTIONS"
        )


def test_pandas_category_membership():
    """Verify that specific methods are in their expected categories."""
    from bioimage_mcp.registry.dynamic.pandas_allowlists import (
        PANDAS_DATAFRAME_METHODS,
        PANDAS_GROUPBY_METHODS,
        PANDAS_TOPLEVEL_FUNCTIONS,
    )

    # Expected methods in DataFrame category
    assert "query" in PANDAS_DATAFRAME_METHODS
    assert "filter" in PANDAS_DATAFRAME_METHODS
    assert "head" in PANDAS_DATAFRAME_METHODS
    assert "tail" in PANDAS_DATAFRAME_METHODS

    # Expected methods in GroupBy category
    assert "mean" in PANDAS_GROUPBY_METHODS
    assert "sum" in PANDAS_GROUPBY_METHODS
    assert "count" in PANDAS_GROUPBY_METHODS

    # Expected top-level functions
    assert "merge" in PANDAS_TOPLEVEL_FUNCTIONS
    assert "concat" in PANDAS_TOPLEVEL_FUNCTIONS
