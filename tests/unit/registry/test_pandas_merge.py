from __future__ import annotations

import pandas as pd
import pytest

from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter, PandasMissingColumnError


@pytest.fixture
def df_a():
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "area": [100.5, 200.3, 50.2],
            "label": ["cell", "cell", "noise"],
        }
    )


@pytest.fixture
def df_b():
    return pd.DataFrame(
        {
            "id": [1, 2, 4],
            "intensity": [0.75, 0.82, 0.60],
            "condition": ["control", "treatment", "treatment"],
        }
    )


def test_merge_inner(df_a, df_b):
    """T042: Test inner join."""
    adapter = PandasAdapter()
    result = adapter.merge(df_a, df_b, on="id", how="inner")

    assert len(result) == 2
    assert list(result["id"]) == [1, 2]
    assert "area" in result.columns
    assert "intensity" in result.columns


def test_merge_left(df_a, df_b):
    """T042: Test left join."""
    adapter = PandasAdapter()
    result = adapter.merge(df_a, df_b, on="id", how="left")

    assert len(result) == 3
    assert list(result["id"]) == [1, 2, 3]
    assert result.iloc[2]["intensity"] is pd.NA or pd.isna(result.iloc[2]["intensity"])


def test_merge_missing_column(df_a, df_b):
    """T046: Test error handling for missing key column."""
    adapter = PandasAdapter()
    with pytest.raises(PandasMissingColumnError) as excinfo:
        adapter.merge(df_a, df_b, on="nonexistent", how="inner")

    assert excinfo.value.code == "PANDAS_MISSING_COLUMN"
    assert "nonexistent" in str(excinfo.value)
    assert "id" in excinfo.value.details["available_columns"]
    assert "hint" in excinfo.value.details


def test_concat_axis_0(df_a):
    """T042: Test vertical concatenation."""
    adapter = PandasAdapter()
    df_c = df_a.copy()
    result = adapter.concat([df_a, df_c], axis=0)

    assert len(result) == 6
    assert list(result.columns) == ["id", "area", "label"]


def test_concat_axis_1(df_a, df_b):
    """T042: Test horizontal concatenation."""
    adapter = PandasAdapter()
    # For horizontal concat, we usually want matching indices or it might create NaNs
    result = adapter.concat([df_a, df_b], axis=1)

    assert len(result) == 3
    assert "area" in result.columns
    assert "intensity" in result.columns
