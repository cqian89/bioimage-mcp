from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pandas as pd
import pytest

from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def native_executor():
    return NativeExecutor()


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_scipy_stats_ttest_ind_equivalence(live_server, native_executor, tmp_path):
    """Test that MCP scipy.stats.ttest_ind_table matches native execution bit-for-bit."""
    # 1. Prepare deterministic input CSVs in an allowed directory
    allowed_tmp = Path("datasets/tmp")
    allowed_tmp.mkdir(parents=True, exist_ok=True)
    table_a_path = allowed_tmp / "table_a.csv"
    table_b_path = allowed_tmp / "table_b.csv"

    try:
        pd.DataFrame({"val": [10.0, 12.0, 11.0, 13.0, 12.0]}).to_csv(table_a_path, index=False)
        pd.DataFrame({"val": [15.0, 14.0, 16.0, 15.0, 17.0]}).to_csv(table_b_path, index=False)

        # 2. Run via MCP
        # Step A: Load tables
        load_a = await live_server.call_tool_checked(
            "run",
            {
                "fn_id": "base.io.table.load",
                "inputs": {},
                "params": {"path": str(table_a_path.absolute())},
            },
        )
        load_b = await live_server.call_tool_checked(
            "run",
            {
                "fn_id": "base.io.table.load",
                "inputs": {},
                "params": {"path": str(table_b_path.absolute())},
            },
        )

        table_a_ref = load_a["outputs"]["table"]
        table_b_ref = load_b["outputs"]["table"]

        # Step B: Run t-test
        mcp_result = await live_server.call_tool_checked(
            "run",
            {
                "fn_id": "base.scipy.stats.ttest_ind_table",
                "inputs": {"table_a": table_a_ref, "table_b": table_b_ref},
                "params": {"column": "val", "equal_var": True, "alternative": "two-sided"},
            },
        )

        if mcp_result.get("status") != "success":
            pytest.fail(f"MCP execution failed: {mcp_result.get('error')}")

        mcp_output_ref = mcp_result["outputs"]["output"]
        mcp_uri = mcp_output_ref["uri"]
        parsed = urlparse(mcp_uri)
        mcp_path = unquote(parsed.path)
        if mcp_path.startswith("/") and len(mcp_path) > 2 and mcp_path[2] == ":":
            mcp_path = mcp_path[1:]

        with open(mcp_path, "r") as f:
            mcp_data = json.load(f)

        # 3. Run via Native Reference Script
        script_path = Path(__file__).parent / "reference_scripts" / "scipy_stats_baseline.py"
        baseline_result = native_executor.run_script(
            "bioimage-mcp-base",
            script_path,
            [
                "--table-a",
                str(table_a_path.absolute()),
                "--table-b",
                str(table_b_path.absolute()),
                "--column",
                "val",
                "--equal-var",
                "true",
            ],
        )

        assert baseline_result["status"] == "success"
        with open(baseline_result["output_path"], "r") as f:
            expected_data = json.load(f)

        # 4. Compare bit-for-bit (exact dict equality)
        # The MCP output may contain extra fields from the Scipy Bunch object,
        # so we only compare the stable fields defined in the baseline.
        for key in expected_data:
            assert mcp_data[key] == expected_data[key], f"Mismatch in field '{key}'"

    finally:
        # Cleanup
        if table_a_path.exists():
            table_a_path.unlink()
        if table_b_path.exists():
            table_b_path.unlink()
        if "baseline_result" in locals() and Path(baseline_result["output_path"]).exists():
            Path(baseline_result["output_path"]).unlink()
