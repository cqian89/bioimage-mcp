import logging
from unittest.mock import patch

import pandas as pd
import pytest

# Note: These imports will fail until the implementation is added (TDD RED phase)
try:
    from bioimage_mcp.errors import BioimageMcpError
    from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter
except ImportError:
    # For TDD we expect this to fail initially.
    # We'll mock them if needed for collection, but the task says "Tests should FAIL".
    PandasAdapter = None
    BioimageMcpError = Exception


@pytest.fixture
def adapter():
    if PandasAdapter is None:
        pytest.fail("PandasAdapter not implemented yet")

    # Use a dummy allowlist for testing
    allowlist = {
        "head": {"summary": "Return the first n rows."},
        "query": {"summary": "Query the columns of a DataFrame with a boolean expression."},
        "describe": {"summary": "Generate descriptive statistics."},
    }
    return PandasAdapter(allowlist=allowlist)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "area": [100.5, 200.0, 150.2, 300.1, 120.5],
            "label": ["A", "B", "A", "C", "B"],
        }
    )


def test_pandas_adapter_dispatch_allowed(adapter, sample_df):
    """Test that adapter can dispatch allowed methods."""
    # Test head()
    result = adapter.execute("head", sample_df, n=2)
    assert len(result) == 2
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["id", "area", "label"]

    # Test describe()
    result = adapter.execute("describe", sample_df)
    assert isinstance(result, pd.DataFrame)
    assert "area" in result.columns


def test_pandas_adapter_object_ref_lookup(adapter):
    """Test that adapter correctly looks up ObjectRef from OBJECT_CACHE."""
    # We mock the cache that would be in the registry adapter
    mock_cache = {}
    df = pd.DataFrame({"x": [10, 20, 30]})
    uri = "obj://pandas.DataFrame/uuid-1234"
    mock_cache[uri] = df

    # We patch the OBJECT_CACHE in the registry adapter module
    # The requirement says the registry adapter will be at:
    # src/bioimage_mcp/registry/dynamic/adapters/pandas.py
    with patch(
        "bioimage_mcp.registry.dynamic.adapters.pandas.OBJECT_CACHE", mock_cache, create=True
    ):
        # We assume PandasAdapter.execute can take a URI and look it up
        result = adapter.execute("head", uri, n=1)
        assert len(result) == 1
        assert result.iloc[0]["x"] == 10


def test_pandas_adapter_denylisted_method(adapter, sample_df):
    """Test that adapter returns structured error when denylisted method is called."""
    # 'to_csv' is NOT in our allowlist, so it should be rejected
    with pytest.raises(BioimageMcpError) as excinfo:
        adapter.execute("to_csv", sample_df)

    # Check for structured error features
    assert excinfo.value.code == "METHOD_NOT_ALLOWED"
    assert "not allowed" in str(excinfo.value)
    assert "to_csv" in str(excinfo.value)
    assert excinfo.value.details is not None


def test_pandas_adapter_query_logging(adapter, sample_df, caplog):
    """Test that adapter logs audit trail for query() executions."""
    with caplog.at_level(logging.INFO):
        # query is allowed in our test fixture
        result = adapter.execute("query", sample_df, expr="area > 150")

    assert len(result) == 3
    assert "Executing pandas query" in caplog.text
    assert "area > 150" in caplog.text
