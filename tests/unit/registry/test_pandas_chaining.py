import pandas as pd
import pytest
import tempfile
from pathlib import Path
from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry
from bioimage_mcp.registry.dynamic.pandas_adapter import OBJECT_CACHE


@pytest.fixture(autouse=True)
def clear_cache():
    OBJECT_CACHE.clear()


def test_pandas_chaining_10_ops():
    """T048: Unit test for ObjectRef chaining (10+ operations)."""
    adapter = PandasAdapterForRegistry()

    # Create sample data
    df = pd.DataFrame(
        {"A": range(20), "B": [i * 2 for i in range(20)], "C": ["group1"] * 10 + ["group2"] * 10}
    )

    # Op 1: Create ObjectRef
    # We need to mock an artifact or use one. PandasAdapterForRegistry._load_table handles URIs.
    # But _execute_constructor is easier.
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        df.to_csv(csv_path, index=False)
        table_ref = {
            "type": "TableRef",
            "uri": csv_path.absolute().as_uri(),
            "path": str(csv_path.absolute()),
            "format": "csv",
        }

        # Op 1: Constructor
        results = adapter.execute("base.pandas.DataFrame", [table_ref], {})
        obj_ref = results[0]
        assert obj_ref["type"] == "ObjectRef"

        current_ref = obj_ref

        # Op 2: query
        results = adapter.execute("base.pandas.DataFrame.query", [current_ref], {"expr": "A > 5"})
        current_ref = results[0]

        # Op 3: sort_values
        results = adapter.execute(
            "base.pandas.DataFrame.sort_values", [current_ref], {"by": "A", "ascending": False}
        )
        current_ref = results[0]

        # Op 4: head
        results = adapter.execute("base.pandas.DataFrame.head", [current_ref], {"n": 10})
        current_ref = results[0]

        # Op 5: reset_index
        results = adapter.execute(
            "base.pandas.DataFrame.reset_index", [current_ref], {"drop": True}
        )
        current_ref = results[0]

        # Op 6: rename
        results = adapter.execute(
            "base.pandas.DataFrame.rename", [current_ref], {"columns": {"B": "B_new"}}
        )
        current_ref = results[0]

        # Op 7: fillna (no-op here but tests the call)
        results = adapter.execute("base.pandas.DataFrame.fillna", [current_ref], {"value": 0})
        current_ref = results[0]

        # Op 8: groupby -> returns GroupByRef
        results = adapter.execute("base.pandas.DataFrame.groupby", [current_ref], {"by": "C"})
        groupby_ref = results[0]
        assert groupby_ref["type"] == "GroupByRef"

        # Op 9: groupby.mean -> returns ObjectRef
        results = adapter.execute("base.pandas.GroupBy.mean", [groupby_ref], {})
        current_ref = results[0]

        # Op 10: reset_index
        results = adapter.execute("base.pandas.DataFrame.reset_index", [current_ref], {})
        current_ref = results[0]

        # Op 11: round
        results = adapter.execute("base.pandas.DataFrame.round", [current_ref], {"decimals": 1})
        current_ref = results[0]

        # Final check
        final_df = OBJECT_CACHE[current_ref["uri"]]
        assert len(final_df) > 0
        assert "A" in final_df.columns
        assert "B_new" in final_df.columns
