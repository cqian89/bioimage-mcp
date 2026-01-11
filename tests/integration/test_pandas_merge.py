from __future__ import annotations

import pytest

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry


def test_integration_pandas_merge_workflow(tmp_path) -> None:
    """T043: Integration test for merge workflow: Load 2 CSVs -> 2 DataFrames -> Merge."""
    adapter = PandasAdapterForRegistry()

    # 1. Create sample CSVs
    csv_a = tmp_path / "table_a.csv"
    csv_a.write_text("id,area,label\n1,100.5,cell\n2,200.3,cell\n3,50.2,noise\n")

    csv_b = tmp_path / "table_b.csv"
    csv_b.write_text("id,intensity,condition\n1,0.75,control\n2,0.82,treatment\n4,0.60,treatment\n")

    # 2. Create TableRef artifacts
    ref_a = {
        "type": "TableRef",
        "uri": csv_a.as_uri(),
        "path": str(csv_a),
        "format": "csv",
    }
    ref_b = {
        "type": "TableRef",
        "uri": csv_b.as_uri(),
        "path": str(csv_b),
        "format": "csv",
    }

    # 3. Convert to ObjectRefs
    res_a = adapter.execute(fn_id="base.pandas.DataFrame", inputs=[ref_a], params={})
    res_b = adapter.execute(fn_id="base.pandas.DataFrame", inputs=[ref_b], params={})
    df_a_ref = res_a[0]
    df_b_ref = res_b[0]

    # 4. Merge
    merge_result = adapter.execute(
        fn_id="base.pandas.merge", inputs=[df_a_ref, df_b_ref], params={"on": "id", "how": "inner"}
    )

    assert len(merge_result) == 1
    merged_ref = merge_result[0]
    assert merged_ref["type"] == "ObjectRef"
    assert merged_ref["metadata"]["shape"] == [2, 5]
    assert set(merged_ref["metadata"]["columns"]) == {
        "id",
        "area",
        "label",
        "intensity",
        "condition",
    }


def test_integration_pandas_concat_workflow(tmp_path) -> None:
    """T043: Integration test for concat workflow."""
    adapter = PandasAdapterForRegistry()

    # 1. Create sample CSVs
    csv_a = tmp_path / "table_a.csv"
    csv_a.write_text("id,val\n1,10\n2,20\n")

    csv_b = tmp_path / "table_b.csv"
    csv_b.write_text("id,val\n3,30\n")

    # 2. Create TableRef artifacts
    ref_a = {"type": "TableRef", "uri": csv_a.as_uri(), "path": str(csv_a), "format": "csv"}
    ref_b = {"type": "TableRef", "uri": csv_b.as_uri(), "path": str(csv_b), "format": "csv"}

    # 3. Concat directly from TableRefs
    # Top-level functions like concat should handle list of artifacts
    concat_result = adapter.execute(
        fn_id="base.pandas.concat", inputs=[ref_a, ref_b], params={"axis": 0}
    )

    assert len(concat_result) == 1
    concat_ref = concat_result[0]
    assert concat_ref["type"] == "ObjectRef"
    assert concat_ref["metadata"]["shape"] == [3, 2]


def test_integration_pandas_merge_missing_column(tmp_path) -> None:
    """T046: Integration test for missing column error in merge."""
    from bioimage_mcp.registry.dynamic.pandas_adapter import PandasMissingColumnError

    adapter = PandasAdapterForRegistry()

    csv_a = tmp_path / "table_a.csv"
    csv_a.write_text("id,area\n1,100.5\n")
    csv_b = tmp_path / "table_b.csv"
    csv_b.write_text("id,intensity\n1,0.75\n")

    ref_a = {"type": "TableRef", "uri": csv_a.as_uri(), "path": str(csv_a), "format": "csv"}
    ref_b = {"type": "TableRef", "uri": csv_b.as_uri(), "path": str(csv_b), "format": "csv"}

    with pytest.raises(PandasMissingColumnError) as excinfo:
        adapter.execute(
            fn_id="base.pandas.merge", inputs=[ref_a, ref_b], params={"on": "nonexistent"}
        )

    assert excinfo.value.code == "PANDAS_MISSING_COLUMN"
    assert "nonexistent" in str(excinfo.value)
    assert "area" in excinfo.value.details["available_columns"]
