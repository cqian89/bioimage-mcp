from __future__ import annotations

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_pandas_merge_discovery() -> None:
    """T041: Verify base.pandas.merge is discoverable and has correct schema."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})

    # Find the merge function
    merge_fn = next((f for f in discovery if f.fn_id == "base.pandas.merge"), None)

    assert merge_fn is not None
    assert merge_fn.name == "merge"
    assert merge_fn.module == "pandas"
    assert "join" in merge_fn.tags
    assert merge_fn.io_pattern == IOPattern.MULTI_TABLE_INPUT

    # Validate parameters
    params = merge_fn.parameters
    assert "how" in params
    assert params["how"].default == "inner"
    assert "on" in params
    assert "left_on" in params
    assert "right_on" in params


def test_pandas_concat_discovery() -> None:
    """T041: Verify base.pandas.concat is discoverable and has correct schema."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})

    # Find the concat function
    concat_fn = next((f for f in discovery if f.fn_id == "base.pandas.concat"), None)

    assert concat_fn is not None
    assert concat_fn.name == "concat"
    assert concat_fn.module == "pandas"
    assert "combine" in concat_fn.tags
    assert concat_fn.io_pattern == IOPattern.MULTI_TABLE_INPUT

    # Validate parameters
    params = concat_fn.parameters
    assert "axis" in params
    assert params["axis"].default == 0
    assert "join" in params
    assert params["join"].default == "outer"
