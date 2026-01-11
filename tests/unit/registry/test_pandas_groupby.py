from __future__ import annotations

import uuid

import pandas as pd
import pytest

from bioimage_mcp.errors import BioimageMcpError
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE
from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry


@pytest.fixture
def sample_df():
    data = {
        "id": [1, 2, 3, 4],
        "area": [100.5, 200.3, 50.2, 300.1],
        "intensity": [0.75, 0.82, 0.95, 0.45],
        "label": ["cell", "cell", "noise", "cell"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def df_ref(sample_df):
    ref_id = str(uuid.uuid4())
    uri = f"obj://default/pandas/{ref_id}"
    OBJECT_CACHE[uri] = sample_df
    return {"ref_id": ref_id, "type": "ObjectRef", "uri": uri, "python_class": "pandas.DataFrame"}


def test_groupby_execution(df_ref, sample_df):
    """T028: Test groupby execution returns GroupByRef."""
    adapter = PandasAdapterForRegistry()

    results = adapter.execute(
        "base.pandas.DataFrame.groupby", inputs=[df_ref], params={"by": "label"}
    )

    assert len(results) == 1
    res = results[0]
    assert res["type"] == "GroupByRef"
    assert res["uri"].startswith("obj://")
    assert "pandas.core.groupby" in res["python_class"]
    assert res["metadata"]["grouped_by"] == ["label"]
    assert res["metadata"]["groups_count"] == 2

    # Verify it's in cache
    assert res["uri"] in OBJECT_CACHE
    assert isinstance(OBJECT_CACHE[res["uri"]], pd.core.groupby.generic.DataFrameGroupBy)


def test_groupby_mean_execution(df_ref):
    """T028: Test mean on GroupByRef."""
    adapter = PandasAdapterForRegistry()

    # 1. GroupBy
    gb_results = adapter.execute(
        "base.pandas.DataFrame.groupby", inputs=[df_ref], params={"by": "label"}
    )
    gb_ref = gb_results[0]

    # 2. Mean
    mean_results = adapter.execute(
        "base.pandas.GroupBy.mean", inputs=[gb_ref], params={"numeric_only": True}
    )

    assert len(mean_results) == 1
    res = mean_results[0]
    assert res["type"] == "ObjectRef"

    df_result = OBJECT_CACHE[res["uri"]]
    assert isinstance(df_result, pd.DataFrame)
    assert len(df_result) == 2
    assert "area" in df_result.columns
    assert "intensity" in df_result.columns

    # Check values
    assert df_result.loc["cell", "area"] == pytest.approx(200.3)
    assert df_result.loc["noise", "area"] == 50.2


def test_groupby_agg_execution(df_ref):
    """T028: Test agg on GroupByRef."""
    adapter = PandasAdapterForRegistry()

    # 1. GroupBy
    gb_results = adapter.execute(
        "base.pandas.DataFrame.groupby", inputs=[df_ref], params={"by": "label"}
    )
    gb_ref = gb_results[0]

    # 2. Agg
    agg_results = adapter.execute(
        "base.pandas.GroupBy.agg", inputs=[gb_ref], params={"func": ["mean", "sum"]}
    )

    assert len(agg_results) == 1
    df_result = OBJECT_CACHE[agg_results[0]["uri"]]
    # Agg with multiple functions returns multi-index columns
    assert ("area", "mean") in df_result.columns
    assert ("area", "sum") in df_result.columns


def test_groupby_missing_column(df_ref):
    """T028: Test error when groupby column is missing."""
    adapter = PandasAdapterForRegistry()

    with pytest.raises(BioimageMcpError) as excinfo:
        adapter.execute(
            "base.pandas.DataFrame.groupby", inputs=[df_ref], params={"by": "nonexistent"}
        )

    err = excinfo.value
    assert err.code == "PANDAS_MISSING_COLUMN"
    assert "nonexistent" in str(err)
    assert "available_columns" in err.details
    assert set(err.details["available_columns"]) == {"id", "area", "intensity", "label"}
