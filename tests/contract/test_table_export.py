from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import load_manifests


@pytest.fixture
def base_tool_manifest():
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, _ = load_manifests([tools_root])
    base = next(m for m in manifests if m.tool_id == "tools.base")
    return base


def test_table_export_exists(base_tool_manifest) -> None:
    """T034: Verify base.io.table.export exists in manifest."""
    fn_ids = {fn.fn_id for fn in base_tool_manifest.functions}
    assert "base.io.table.export" in fn_ids, "base.io.table.export missing from manifest"


def test_table_export_schema(base_tool_manifest) -> None:
    """T034: Verify base.io.table.export schema matches spec."""
    table_export = next(
        (fn for fn in base_tool_manifest.functions if fn.fn_id == "base.io.table.export"), None
    )
    if not table_export:
        pytest.fail("base.io.table.export not found in manifest")

    # Check inputs
    input_names = {i.name for i in table_export.inputs}
    assert "data" in input_names, "Missing 'data' input"

    # Check data input types
    data_input = next(i for i in table_export.inputs if i.name == "data")
    artifact_types = data_input.artifact_type
    if isinstance(artifact_types, str):
        artifact_types = [artifact_types]
    assert "TableRef" in artifact_types
    assert "ObjectRef" in artifact_types

    # Check params
    assert table_export.params_schema, "Missing params_schema"
    props = table_export.params_schema.get("properties", {})
    assert "dest_path" in props, "Missing 'dest_path' parameter"
    assert "sep" in props, "Missing 'sep' parameter"

    # Check outputs
    assert len(table_export.outputs) == 1, "Should have exactly one output"
    assert table_export.outputs[0].artifact_type == "TableRef", "Output must be TableRef"
