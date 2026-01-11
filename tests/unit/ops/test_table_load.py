from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

# Add tools/base to sys.path to find bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

# TDD RED: we expect these to potentially fail or not exist yet
try:
    from bioimage_mcp_base.ops.io import PathNotAllowedError, table_load
except ImportError:
    table_load = None
    PathNotAllowedError = Exception


@pytest.fixture
def check_implemented():
    if table_load is None:
        pytest.fail("table_load not implemented in bioimage_mcp_base.ops.io")


def test_table_load_csv_explicit_delimiter(tmp_path, check_implemented) -> None:
    """Test loading CSV with an explicit semicolon delimiter."""
    csv_path = tmp_path / "test_explicit.csv"
    csv_path.write_text("id;area;intensity\n1;100.5;0.75\n2;200.3;0.82")

    # Mock allowlist to include tmp_path
    import json
    import os

    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps([str(tmp_path)])

    result = table_load(
        inputs={}, params={"path": str(csv_path), "delimiter": ";"}, work_dir=tmp_path
    )

    assert "outputs" in result
    table = result["outputs"]["table"]
    assert table["type"] == "TableRef"
    assert table["columns"] == ["id", "area", "intensity"]
    assert table["row_count"] == 2
    assert table["delimiter"] == ";"
    assert table["format"] == "csv"


def test_table_load_auto_delimiter_detection(tmp_path, check_implemented) -> None:
    """Test auto-detection of comma, tab, and semicolon delimiters."""
    import json
    import os

    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps([str(tmp_path)])

    # 1. Comma
    comma_path = tmp_path / "comma.csv"
    comma_path.write_text("id,area\n1,100.5\n2,200.3")
    res = table_load(inputs={}, params={"path": str(comma_path)}, work_dir=tmp_path)
    assert res["outputs"]["table"]["delimiter"] == ","

    # 2. Tab
    tab_path = tmp_path / "tab.tsv"
    tab_path.write_text("id\tarea\n1\t100.5\n2\t200.3")
    res = table_load(inputs={}, params={"path": str(tab_path)}, work_dir=tmp_path)
    assert res["outputs"]["table"]["delimiter"] == "\t"

    # 3. Semicolon
    semi_path = tmp_path / "semi.txt"
    semi_path.write_text("id;area\n1;100.5\n2;200.3")
    res = table_load(inputs={}, params={"path": str(semi_path)}, work_dir=tmp_path)
    assert res["outputs"]["table"]["delimiter"] == ";"


def test_table_load_path_allowlist_validation(
    tmp_path, monkeypatch, caplog, check_implemented
) -> None:
    """Test that paths outside the allowlist are rejected with structured errors and logging."""
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    # Set explicit allowlist
    import json

    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(allowed_dir)]))

    outside_path = tmp_path / "outside.csv"
    outside_path.write_text("id,area\n1,100")

    with caplog.at_level(logging.INFO):
        with pytest.raises(PathNotAllowedError) as excinfo:
            table_load(inputs={}, params={"path": str(outside_path)}, work_dir=tmp_path)

    # Verify structured error shape (T012)
    # The PathNotAllowedError should have a 'code' attribute
    assert getattr(excinfo.value, "code", None) == "PATH_NOT_ALLOWED"

    # Verify permission decision logging (FR-016)
    # Expected format: "Permission DENIED for READ: ... (Reason: ...)"
    assert "Permission DENIED" in caplog.text
    assert "READ" in caplog.text.upper()
    assert str(outside_path) in caplog.text


def test_table_load_invalid_csv_format(tmp_path, check_implemented) -> None:
    """Test handling of invalid file content."""
    import json
    import os

    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps([str(tmp_path)])

    bad_path = tmp_path / "bad.csv"
    bad_path.write_bytes(b"\xff\xfe\x00\x00")  # Invalid encoding or binary

    with pytest.raises(Exception):  # Should raise some descriptive error
        table_load(inputs={}, params={"path": str(bad_path)}, work_dir=tmp_path)
