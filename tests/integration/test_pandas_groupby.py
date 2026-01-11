from __future__ import annotations

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry


def test_integration_pandas_groupby_workflow(tmp_path) -> None:
    """T029: Integration test for groupby workflow: Load CSV -> DataFrame -> GroupBy -> Mean -> Agg."""
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
    constructor_result = adapter.execute(
        fn_id="base.pandas.DataFrame", inputs=[table_ref], params={}
    )
    df_ref = constructor_result[0]

    # 4. GroupBy "label"
    groupby_result = adapter.execute(
        fn_id="base.pandas.DataFrame.groupby", inputs=[df_ref], params={"by": "label"}
    )
    assert len(groupby_result) == 1
    gb_ref = groupby_result[0]
    assert gb_ref["type"] == "GroupByRef"
    assert gb_ref["metadata"]["grouped_by"] == ["label"]
    assert gb_ref["metadata"]["groups_count"] == 2

    # 5. Mean
    mean_result = adapter.execute(
        fn_id="base.pandas.GroupBy.mean", inputs=[gb_ref], params={"numeric_only": True}
    )
    assert len(mean_result) == 1
    res_df_ref = mean_result[0]
    assert res_df_ref["type"] == "ObjectRef"
    assert res_df_ref["metadata"]["shape"] == [2, 3]  # label is index, cols: id, area, intensity

    # 6. Agg
    agg_result = adapter.execute(
        fn_id="base.pandas.GroupBy.agg", inputs=[gb_ref], params={"func": ["mean", "sum"]}
    )
    assert len(agg_result) == 1
    agg_df_ref = agg_result[0]
    assert agg_df_ref["type"] == "ObjectRef"
    # columns will be multi-indexed if multiple funcs are passed
    # In _handle_result, columns are just converted to list
    # pd.MultiIndex.tolist() returns list of tuples
    cols = agg_df_ref["metadata"]["columns"]
    assert any("mean" in str(c) for c in cols)
    assert any("sum" in str(c) for c in cols)
