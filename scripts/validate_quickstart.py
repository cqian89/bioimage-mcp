import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from bioimage_mcp_base.ops.io import table_export, table_load

from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter


def validate_quickstart():
    print("Running Quickstart Validation...")

    # Setup directories
    data_dir = Path("datasets/sample_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(".bioimage-mcp/work")
    work_dir.mkdir(parents=True, exist_ok=True)

    # Create sample Cellpose measurement file
    csv_path = data_dir / "measurements.csv"
    data = {
        "label_id": np.arange(1, 11),
        "area": [200, 600, 150, 800, 300, 1200, 450, 900, 100, 550],
        "mean_intensity": [50, 120, 40, 150, 60, 200, 80, 180, 30, 110],
        "class_name": ["A", "B", "A", "B", "A", "C", "B", "C", "A", "B"],
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    print(f"Created sample data at {csv_path}")

    # Set environment for allowed paths
    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps([str(Path.cwd().resolve())])
    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"] = json.dumps([str(Path.cwd().resolve())])

    # 1. Load a CSV Table
    print("Step 1: Loading Table...")
    params1 = {"path": str(csv_path), "delimiter": ","}
    res1 = table_load(inputs={}, params=params1, work_dir=work_dir)
    table_ref = res1["outputs"]["table"]
    print(f"Loaded Table: {table_ref['row_count']} rows")

    # 2. Filter with query()
    print("Step 2: Filtering with query()...")
    adapter = PandasAdapter()
    # We simulate the tool execution here.
    # In a real MCP call, the registry would handle the conversion from TableRef to DataFrame.
    df_loaded = pd.read_csv(table_ref["path"])
    filtered_df = adapter.execute("query", df_loaded, expr="area > 500")
    print(f"Filtered: {len(filtered_df)} rows")

    # 3. GroupBy and Aggregate
    print("Step 3: GroupBy and Aggregate...")
    grouped = adapter.execute("groupby", filtered_df, by="class_name")
    # For aggregation, we need to handle the GroupBy object.
    # The adapter expects a DataFrame but groupby returns a GroupBy object.
    # Our adapter's execute method handles this by calling the method on the object.
    agg_df = adapter.execute("mean", grouped, numeric_only=True)
    print("Aggregated Results:")
    print(agg_df)

    # 4. Export Results
    print("Step 4: Exporting Results...")
    dest_path = results_dir / "summary.csv"
    # table_export expects inputs["data"] to be a Ref
    # We'll mock an ObjectRef for the aggregated DataFrame
    agg_ref = {"type": "ObjectRef", "uri": "obj://internal/test/agg_df"}
    # We need to put it in the cache that table_export uses
    from bioimage_mcp_base.entrypoint import _OBJECT_CACHE

    _OBJECT_CACHE["obj://internal/test/agg_df"] = agg_df

    params4 = {"dest_path": str(dest_path), "sep": ","}
    res4 = table_export(inputs={"data": agg_ref}, params=params4, work_dir=work_dir)
    exported_ref = res4["outputs"]["table"]
    print(f"Exported to {exported_ref['path']}")

    # Verification
    assert exported_ref["row_count"] == len(agg_df)
    assert Path(exported_ref["path"]).exists()
    print("Quickstart Validation SUCCESS!")


if __name__ == "__main__":
    validate_quickstart()
