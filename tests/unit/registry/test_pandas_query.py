import logging
from unittest.mock import patch

import pandas as pd
import pytest

from bioimage_mcp.errors import BioimageMcpError
from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter


@pytest.fixture
def adapter():
    # Use the default allowlist which includes 'query'
    return PandasAdapter()


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "area": [100.5, 200.3, 50.2, 300.1],
            "intensity": [0.75, 0.82, 0.95, 0.45],
            "label": ["cell", "cell", "noise", "cell"],
        }
    )


def test_query_single_filter(adapter, sample_df):
    """T020: Test single filter 'area > 100'."""
    result = adapter.execute("query", sample_df, expr="area > 100")
    assert len(result) == 3
    assert all(result["area"] > 100)
    assert list(result["id"]) == [1, 2, 4]


def test_query_compound_filter(adapter, sample_df):
    """T020: Test compound filter 'area > 100 and intensity < 0.5'."""
    result = adapter.execute("query", sample_df, expr="area > 100 and intensity < 0.5")
    assert len(result) == 1
    assert result.iloc[0]["id"] == 4


def test_query_invalid_syntax(adapter, sample_df):
    """T020: Test invalid syntax returns PANDAS_INVALID_QUERY error."""
    with pytest.raises(BioimageMcpError) as excinfo:
        adapter.execute("query", sample_df, expr="area >")

    assert excinfo.value.code == "PANDAS_INVALID_QUERY"


def test_query_at_var_blocked(adapter, sample_df):
    """T020: Test that @var access is blocked for security."""
    my_var = 100
    with pytest.raises(BioimageMcpError) as excinfo:
        adapter.execute("query", sample_df, expr="area > @my_var")

    assert (
        "local variable access" in str(excinfo.value).lower()
        or "blocked" in str(excinfo.value).lower()
    )


def test_query_audit_logging(adapter, sample_df, caplog):
    """T020: Test audit logging captures expression and result row count."""
    # We need to simulate an ObjectRef to test ref_id logging if required,
    # but the requirement says "input ref_id" which implies we might need to pass a URI.

    mock_cache = {"obj://df/1": sample_df}
    with patch(
        "bioimage_mcp.registry.dynamic.pandas_adapter.OBJECT_CACHE", mock_cache, create=True
    ):
        with caplog.at_level(logging.INFO):
            result = adapter.execute("query", "obj://df/1", expr="area > 200")

    assert len(result) == 2
    assert "area > 200" in caplog.text
    assert "obj://df/1" in caplog.text
    assert "rows=2" in caplog.text or "count=2" in caplog.text
