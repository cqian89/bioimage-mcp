import time

import numpy as np
import pandas as pd
import pytest

from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter


@pytest.mark.slow
def test_performance_large_table_filter():
    """
    T060: Performance validation: 100,000-row table filter in <2 seconds
    """
    # 1. Create a 100,000 row DataFrame
    num_rows = 100_000
    data = {
        "id": np.arange(num_rows),
        "area": np.random.uniform(0, 1000, size=num_rows),
        "intensity": np.random.uniform(0, 255, size=num_rows),
        "label": [f"cell_{i}" for i in range(num_rows)],
    }
    df = pd.DataFrame(data)

    adapter = PandasAdapter()

    # 2. Runs query("area > 500")
    start_time = time.perf_counter()
    result = adapter.execute("query", df, expr="area > 500")
    end_time = time.perf_counter()

    duration = end_time - start_time

    # 3. Asserts completion in <2 seconds
    print(f"\nFiltered {num_rows} rows in {duration:.4f} seconds")
    assert duration < 2.0
    assert len(result) < num_rows
    assert len(result) > 0


def test_apply_numpy_restricted():
    """
    Test T055: Restricted apply() with whitelisted numpy functions
    """
    adapter = PandasAdapter()
    df = pd.DataFrame({"A": [1, 4, 9, 16], "B": [10, 20, 30, 40]})

    # Test whitelisted function
    result = adapter.execute("apply_numpy", df, func="sqrt")
    assert result["A"].tolist() == [1.0, 2.0, 3.0, 4.0]

    # Test denied function (not in whitelisted numpy funcs for apply_numpy)
    with pytest.raises(Exception) as excinfo:
        adapter.execute("apply_numpy", df, func="invalid_func")
    assert "not in the allowlist" in str(excinfo.value)


def test_table_load_empty_with_headers(tmp_path):
    """
    T057: Empty file handling (headers only -> row_count=0)
    """
    from bioimage_mcp_base.ops.io import table_load

    csv_file = tmp_path / "empty_headers.csv"
    csv_file.write_text("ID,Area,Intensity\n")

    # Mocking work_dir and inputs
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Need to set environment variable for allowed paths
    import json
    import os

    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps([str(tmp_path)])

    params = {"path": str(csv_file)}
    result = table_load(inputs={}, params=params, work_dir=work_dir)

    table_ref = result["outputs"]["table"]
    assert table_ref["row_count"] == 0
    assert table_ref["columns"] == ["ID", "Area", "Intensity"]
