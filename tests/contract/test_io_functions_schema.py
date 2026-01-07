from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import load_manifests

EXPECTED_IO_FUNCTIONS = {
    "base.io.bioimage.load",
    "base.io.bioimage.inspect",
    "base.io.bioimage.slice",
    "base.io.bioimage.validate",
    "base.io.bioimage.get_supported_formats",
    "base.io.bioimage.export",
}


@pytest.fixture
def base_tool_manifest():
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, _ = load_manifests([tools_root])
    base = next(m for m in manifests if m.tool_id == "tools.base")
    return base


def test_io_functions_existence(base_tool_manifest) -> None:
    """T007: Verify all 6 new I/O functions exist in manifest."""
    fn_ids = {fn.fn_id for fn in base_tool_manifest.functions}
    missing = EXPECTED_IO_FUNCTIONS - fn_ids
    assert not missing, f"Missing functions in manifest: {missing}"


def test_base_tool_version_bumped(base_tool_manifest) -> None:
    """T053: Assert tool_version is bumped (not 0.1.0)."""
    assert base_tool_manifest.tool_version != "0.1.0", (
        "tool_version must be bumped (expected 0.2.0+)"
    )


def test_io_functions_schema_completeness(base_tool_manifest) -> None:
    """T054: Assert schema docs completeness for all 6 functions."""
    io_fns = [fn for fn in base_tool_manifest.functions if fn.fn_id in EXPECTED_IO_FUNCTIONS]

    # First ensure we found them all (existence test handles this too but good for context)
    assert len(io_fns) == len(EXPECTED_IO_FUNCTIONS)

    for fn in io_fns:
        assert fn.description, f"Function {fn.fn_id} missing description"
        assert len(fn.description) > 10, f"Function {fn.fn_id} description too short"

        assert fn.params_schema, f"Function {fn.fn_id} missing params_schema"
        assert fn.params_schema.get("type") == "object", (
            f"Function {fn.fn_id} params_schema must be type: object"
        )

        assert fn.tags, f"Function {fn.fn_id} missing tags"
        assert len(fn.tags) > 0, f"Function {fn.fn_id} must have at least one tag"

        # Check for examples in complex params (T054)
        if fn.fn_id == "base.io.bioimage.slice":
            assert "examples" in fn.params_schema, (
                f"Function {fn.fn_id} must have examples in params_schema due to complex SliceSpec"
            )
            assert len(fn.params_schema["examples"]) >= 2, (
                f"Function {fn.fn_id} should have at least 2 examples"
            )


def test_deprecated_io_export_absent(base_tool_manifest) -> None:
    """T052: Assert deprecated base.bioio.export is absent from manifest."""
    fn_ids = {fn.fn_id for fn in base_tool_manifest.functions}
    assert "base.bioio.export" not in fn_ids, (
        "Deprecated function base.bioio.export still present in manifest"
    )
