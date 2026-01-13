from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry


@pytest.mark.slow
def test_full_pandas_pipeline(tmp_path):
    """T047: Integration test for full chain: load → filter → groupby → mean → export."""
    adapter = PandasAdapterForRegistry()

    # 1. Create sample CSV
    csv_path = tmp_path / "data.csv"
    df = pd.DataFrame(
        {
            "id": range(100),
            "value": [i * 1.5 for i in range(100)],
            "category": ["A", "B", "C", "D"] * 25,
        }
    )
    df.to_csv(csv_path, index=False)

    table_ref = {
        "type": "TableRef",
        "uri": csv_path.as_uri(),
        "path": str(csv_path),
        "format": "csv",
    }

    # 2. DataFrame constructor
    res = adapter.execute("base.pandas.DataFrame", [table_ref], {})
    df_ref = res[0]

    # 3. Filter (query)
    res = adapter.execute("base.pandas.DataFrame.query", [df_ref], {"expr": "value > 10"})
    filtered_ref = res[0]

    # 4. GroupBy
    res = adapter.execute("base.pandas.DataFrame.groupby", [filtered_ref], {"by": "category"})
    groupby_ref = res[0]

    # 5. Mean
    res = adapter.execute("base.pandas.GroupBy.mean", [groupby_ref], {})
    mean_ref = res[0]

    # 6. Export (to_tableref)
    # We use to_tableref as requested in T049
    res = adapter.execute(
        "base.pandas.DataFrame.to_tableref", [mean_ref], {"format": "csv"}, work_dir=tmp_path
    )
    final_table = res[0]

    assert final_table["type"] == "TableRef"
    assert final_table["format"] == "csv"
    assert Path(final_table["path"]).exists()
    assert final_table["path"].endswith(".csv")

    # Verify content
    final_df = pd.read_csv(final_table["path"])

    assert len(final_df) == 4  # categories A, B, C, D
    assert "value" in final_df.columns
