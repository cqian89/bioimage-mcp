from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

# Add tools/base to sys.path to find bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

# TDD RED: table_load doesn't exist yet
try:
    from bioimage_mcp_base.ops.io import table_load
except ImportError:
    table_load = None


@pytest.fixture
def check_implemented():
    if table_load is None:
        pytest.fail("table_load not implemented in bioimage_mcp_base.ops.io")


def test_integration_table_load_csv(tmp_path, monkeypatch, check_implemented) -> None:
    """T013: Integration test loading a real sample CSV file."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))

    csv_path = tmp_path / "measurements.csv"
    csv_content = (
        "id,area,intensity,label\n1,100.5,0.75,cell\n2,200.3,0.82,cell\n3,150.2,0.65,nucleus"
    )
    csv_path.write_text(csv_content)

    result = table_load(inputs={}, params={"path": str(csv_path)}, work_dir=tmp_path)

    assert "outputs" in result
    table_ref = result["outputs"]["table"]
    assert table_ref["type"] == "TableRef"
    assert table_ref["format"] == "csv"
    assert table_ref["columns"] == ["id", "area", "intensity", "label"]
    assert table_ref["row_count"] == 3
    assert table_ref["uri"] == f"file://{csv_path}"
    assert table_ref["delimiter"] == ","


@pytest.mark.slow
def test_performance_table_load_large_csv(tmp_path, monkeypatch, check_implemented) -> None:
    """T013: Assert SC-001 load <= 5s for ~10MB input."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))

    # Create ~10MB CSV
    # Each row is approx 30-40 bytes. 250,000 rows ~= 10MB.
    large_csv = tmp_path / "large_performance.csv"
    num_rows = 250_000

    lines = ["id,area,intensity,label\n"]
    for i in range(num_rows):
        lines.append(f"{i},{i * 1.5},{i / num_rows},cell\n")

    large_csv.write_text("".join(lines))

    start_time = time.time()
    result = table_load(inputs={}, params={"path": str(large_csv)}, work_dir=tmp_path)
    elapsed = time.time() - start_time

    assert result["outputs"]["table"]["row_count"] == num_rows
    assert elapsed <= 5.0, f"Loading ~10MB CSV took {elapsed:.2f}s, exceeding 5s limit"
