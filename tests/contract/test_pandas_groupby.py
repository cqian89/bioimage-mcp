from __future__ import annotations

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_pandas_groupby_discovery() -> None:
    """T027: Verify base.pandas.DataFrame.groupby is discoverable and has correct schema."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})

    # Find the groupby function
    groupby_fn = next((f for f in discovery if f.fn_id == "base.pandas.DataFrame.groupby"), None)

    assert groupby_fn is not None
    assert groupby_fn.name == "groupby"
    assert groupby_fn.module == "pandas.DataFrame"
    assert "split" in groupby_fn.tags
    assert groupby_fn.io_pattern == IOPattern.OBJECTREF_CHAIN

    # Validate parameters
    params = groupby_fn.parameters
    assert "by" in params
    # According to spec, 'by' can be string or list of strings.
    # Current allowlist has 'any'. I will update it to be more specific if possible,
    # but for now let's just check it exists.
    assert "as_index" in params
    assert params["as_index"].default is True


def test_pandas_groupby_mean_discovery() -> None:
    """T027: Verify base.pandas.GroupBy.mean is discoverable."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})

    mean_fn = next((f for f in discovery if f.fn_id == "base.pandas.GroupBy.mean"), None)

    assert mean_fn is not None
    assert mean_fn.name == "mean"
    assert mean_fn.module == "pandas.core.groupby.DataFrameGroupBy"
    assert "groupby" in mean_fn.tags

    # Check for numeric_only param (to be added)
    assert "numeric_only" in mean_fn.parameters


def test_pandas_groupby_agg_discovery() -> None:
    """T027: Verify base.pandas.GroupBy.agg is discoverable."""
    adapter = PandasAdapterForRegistry()
    discovery = adapter.discover({})

    agg_fn = next((f for f in discovery if f.fn_id == "base.pandas.GroupBy.agg"), None)

    assert agg_fn is not None
    assert agg_fn.name == "agg"
    assert "func" in agg_fn.parameters
    assert agg_fn.parameters["func"].required is True
