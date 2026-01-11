from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

# Add tools/base to sys.path to find bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

try:
    from bioimage_mcp_base.ops.io import table_export, table_load
except ImportError:
    table_load = None
    table_export = None


@pytest.fixture
def check_implemented():
    if table_export is None:
        pytest.fail("table_export not implemented in bioimage_mcp_base.ops.io")


def test_integration_table_export_workflow(tmp_path, monkeypatch, check_implemented) -> None:
    """T036: Integration test for export workflow: Load -> Export -> Load."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path.resolve())]))
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path.resolve())]))

    # 1. Create initial CSV
    csv_path = tmp_path / "input.csv"
    df = pd.DataFrame({"id": [1, 2], "value": [3.141592653589793, 2.718281828459045]})
    df.to_csv(csv_path, index=False)

    # 2. Load it
    load_result = table_load(inputs={}, params={"path": str(csv_path)}, work_dir=tmp_path)
    table_ref = load_result["outputs"]["table"]

    # 3. Export it to TSV
    tsv_path = tmp_path / "output.tsv"
    export_result = table_export(
        inputs={"data": table_ref},
        params={"dest_path": str(tsv_path), "sep": "\t"},
        work_dir=tmp_path,
    )

    exported_ref = export_result["outputs"]["table"]
    assert tsv_path.exists()
    assert exported_ref["format"] == "tsv"

    # 4. Load the exported TSV back
    # We use table_load to verify it can read what we wrote
    reload_result = table_load(inputs={}, params={"path": str(tsv_path)}, work_dir=tmp_path)
    reloaded_table_ref = reload_result["outputs"]["table"]
    assert reloaded_table_ref["row_count"] == 2

    reloaded_df = pd.read_csv(tsv_path, sep="\t")

    # 5. Verify data integrity (especially precision)
    assert reloaded_df.loc[0, "value"] == pytest.approx(3.141592653589793, abs=1e-14)
    assert len(reloaded_df) == 2
