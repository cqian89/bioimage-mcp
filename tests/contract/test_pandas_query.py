from __future__ import annotations

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_pandas_query_discovery() -> None:
    """T019: Verify base.pandas.DataFrame.query is discoverable and has correct schema."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})

    # Find the query function
    query_fn = next((f for f in discovery if f.fn_id == "base.pandas.DataFrame.query"), None)

    assert query_fn is not None
    assert query_fn.name == "query"
    assert query_fn.module == "pandas.DataFrame"
    assert "filter" in query_fn.tags

    # Validate expr parameter is required
    assert "expr" in query_fn.parameters
    assert query_fn.parameters["expr"].required is True
    assert query_fn.parameters["expr"].type == "string"

    # Validate IO pattern - it should be OBJECTREF_CHAIN which implies ObjectRef in/out
    # The spec says it accepts [TableRef, ObjectRef] input.
    # In PandasAdapterForRegistry.discover, the io_pattern is set to OBJECTREF_CHAIN for most methods.
    assert query_fn.io_pattern == IOPattern.OBJECTREF_CHAIN


def test_pandas_query_params_schema() -> None:
    """T019: Validate detailed parameter schema for query."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})
    query_fn = next((f for f in discovery if f.fn_id == "base.pandas.DataFrame.query"), None)

    params = query_fn.parameters
    assert "expr" in params
    assert "inplace" in params
    assert params["inplace"].default is False
    assert params["inplace"].required is False
