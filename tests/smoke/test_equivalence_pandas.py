from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def executor():
    return NativeExecutor()


@pytest.fixture
def sample_csv():
    # Use measurements.csv from sample_data
    path = Path("datasets/sample_data/measurements.csv")
    if not path.exists():
        pytest.skip(f"Dataset missing: {path}")
    return path


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_pandas_equivalence(live_server, helper, executor, sample_csv, tmp_path):
    """Compare MCP pandas operations vs native execution."""

    # 1. Native Execution
    script_path = Path("tests/smoke/reference_scripts/pandas_baseline.py")
    native_res = executor.run_script(
        env_name="bioimage-mcp-base",
        script_path=script_path,
        args=[str(sample_csv)],
    )

    native_desc = pd.DataFrame(
        native_res["describe"]["data"],
        index=native_res["describe"]["index"],
        columns=native_res["describe"]["columns"],
    )
    native_desc.index.names = native_res["describe"]["index_names"]

    native_gb = pd.DataFrame(
        native_res["groupby"]["data"],
        index=native_res["groupby"]["index"],
        columns=native_res["groupby"]["columns"],
    )
    native_gb.index.names = native_res["groupby"]["index_names"]

    # 2. MCP Execution
    # 2a. Load CSV
    load_res = await live_server.call_tool(
        "run",
        {
            "id": "base.io.table.load",
            "inputs": {},
            "params": {"path": str(sample_csv)},
        },
    )
    assert load_res.get("status") == "success"
    table_ref = load_res["outputs"]["table"]

    # 2b. Convert to DataFrame (ObjectRef)
    # Note: pandas adapter expects ref_id string, not full artifact dict
    to_df_res = await live_server.call_tool(
        "run",
        {
            "id": "base.pandas.DataFrame",
            "inputs": {"image": table_ref["ref_id"]},
        },
    )
    assert to_df_res.get("status") == "success", f"Conversion failed: {to_df_res}"
    df_ref = to_df_res["outputs"]["output"]

    # 2c. Describe
    describe_res = await live_server.call_tool(
        "run",
        {
            "id": "base.pandas.DataFrame.describe",
            "inputs": {"image": df_ref},
        },
    )
    assert describe_res.get("status") == "success", f"Describe failed: {describe_res}"
    desc_obj_ref = describe_res["outputs"]["output"]

    # 2d. Groupby mean
    groupby_res = await live_server.call_tool(
        "run",
        {
            "id": "base.pandas.DataFrame.groupby",
            "inputs": {"image": df_ref},
            "params": {"by": "class_name"},
        },
    )
    assert groupby_res.get("status") == "success"
    gb_obj_ref = groupby_res["outputs"]["output"]

    mean_res = await live_server.call_tool(
        "run",
        {
            "id": "base.pandas.GroupBy.mean",
            "inputs": {"image": gb_obj_ref},
        },
    )
    assert mean_res.get("status") == "success"
    mean_obj_ref = mean_res["outputs"]["output"]

    # 2e. Export results to compare
    async def get_df_from_ref(ref, name):
        # Use a path in the allowed artifacts directory
        # We'll use a unique name to avoid collisions
        import uuid

        dest_path = Path.home() / ".bioimage-mcp" / "artifacts" / f"{name}_{uuid.uuid4()}.csv"
        # Ensure parent exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        export_res = await live_server.call_tool(
            "run",
            {
                "id": "base.io.table.export",
                "inputs": {"data": ref},
                "params": {"dest_path": str(dest_path)},
            },
        )
        assert export_res.get("status") == "success", f"Export failed: {export_res}"

        # For describe and groupby, we expect an index in the CSV
        df = pd.read_csv(dest_path, index_col=0)

        # Clean up
        if dest_path.exists():
            dest_path.unlink()
        return df

    mcp_desc = await get_df_from_ref(desc_obj_ref, "desc")
    mcp_gb = await get_df_from_ref(mean_obj_ref, "gb")

    # 3. Compare
    # Cast numeric columns to float to avoid int/float mismatch from CSV roundtrip
    for df in [mcp_desc, native_desc, mcp_gb, native_gb]:
        for col in df.select_dtypes(include=["number"]).columns:
            df[col] = df[col].astype(float)

    helper.assert_table_equivalent(mcp_desc, native_desc)
    helper.assert_table_equivalent(mcp_gb, native_gb)
