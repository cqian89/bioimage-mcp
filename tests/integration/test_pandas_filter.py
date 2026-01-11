from __future__ import annotations

import pytest

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry


def test_integration_pandas_filter_workflow(tmp_path) -> None:
    """T021: Integration test for filter workflow: Load CSV -> DataFrame -> query."""
    adapter = PandasAdapterForRegistry()

    # 1. Create sample CSV
    csv_path = tmp_path / "data.csv"
    csv_content = (
        "id,area,intensity,label\n"
        "1,100.5,0.75,cell\n"
        "2,200.3,0.82,cell\n"
        "3,50.2,0.95,noise\n"
        "4,300.1,0.45,cell\n"
    )
    csv_path.write_text(csv_content)

    # 2. Create TableRef artifact
    table_ref = {
        "type": "TableRef",
        "uri": csv_path.as_uri(),
        "path": str(csv_path),
        "format": "csv",
        "metadata": {"columns": ["id", "area", "intensity", "label"], "row_count": 4},
    }

    # 3. Convert to ObjectRef (DataFrame constructor)
    # fn_id="base.pandas.DataFrame"
    constructor_result = adapter.execute(
        fn_id="base.pandas.DataFrame", inputs=[table_ref], params={}
    )

    assert len(constructor_result) == 1
    df_ref = constructor_result[0]
    assert df_ref["type"] == "ObjectRef"
    assert df_ref["python_class"] == "pandas.DataFrame"

    # 4. Filter: area > 100
    # fn_id="base.pandas.DataFrame.query"
    query_result_1 = adapter.execute(
        fn_id="base.pandas.DataFrame.query", inputs=[df_ref], params={"expr": "area > 100"}
    )

    assert len(query_result_1) == 1
    result_ref_1 = query_result_1[0]
    assert result_ref_1["metadata"]["shape"][0] == 3  # 3 rows match

    # 5. Compound Filter: area > 100 and intensity < 0.5
    query_result_2 = adapter.execute(
        fn_id="base.pandas.DataFrame.query",
        inputs=[df_ref],
        params={"expr": "area > 100 and intensity < 0.5"},
    )

    assert len(query_result_2) == 1
    result_ref_2 = query_result_2[0]
    assert result_ref_2["metadata"]["shape"][0] == 1  # Only row 4 matches
    assert result_ref_2["metadata"]["columns"] == ["id", "area", "intensity", "label"]


def test_integration_pandas_query_invalid_workflow(tmp_path) -> None:
    """T021: Verify error handling in integration workflow."""
    adapter = PandasAdapterForRegistry()

    # Create empty DF
    df_ref = {
        "type": "ObjectRef",
        "uri": "obj://pandas.DataFrame/non-existent",  # This will fail if not in cache
        "python_class": "pandas.DataFrame",
        "storage_type": "memory",
    }

    # We expect ValueError because URI is not in cache (actually our implementation raises ValueError)
    with pytest.raises(ValueError, match="not found in memory cache"):
        adapter.execute(
            fn_id="base.pandas.DataFrame.query", inputs=[df_ref], params={"expr": "area > 100"}
        )
