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


def test_table_load_exists(base_tool_manifest) -> None:
    """T011: Verify base.io.table.load exists in manifest."""
    fn_ids = {fn.fn_id for fn in base_tool_manifest.functions}
    assert "base.io.table.load" in fn_ids, "base.io.table.load missing from manifest"


def test_table_load_schema(base_tool_manifest) -> None:
    """T011: Verify base.io.table.load schema matches spec."""
    table_load = next(
        (fn for fn in base_tool_manifest.functions if fn.fn_id == "base.io.table.load"), None
    )
    if not table_load:
        pytest.fail("base.io.table.load not found in manifest")

    # Check params
    assert table_load.params_schema, "Missing params_schema"
    props = table_load.params_schema.get("properties", {})

    # The spec says 'path' is an input, but in manifest it often goes to params for path-based tools
    # We accept it in either place for now, but usually it's in params for load functions
    assert "path" in props or any(i.name == "path" for i in table_load.inputs), (
        "Required input 'path' missing"
    )

    assert "delimiter" in props, "Missing 'delimiter' parameter"
    assert "format" in props, "Missing 'format' parameter"

    # Check outputs
    assert len(table_load.outputs) == 1, "Should have exactly one output"
    assert table_load.outputs[0].artifact_type == "TableRef", "Output must be TableRef"
