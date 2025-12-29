import pytest
from pathlib import Path
from bioimage_mcp.registry.loader import load_manifest_file


def test_overlay_fn_id_validation_missing_target(tmp_path):
    """Verify that overlays for non-existent functions cause a warning/error."""
    manifest_yaml = """
manifest_version: "0.0"
tool_id: tools.test
tool_version: "0.1.0"
env_id: bioimage-mcp-test
entrypoint: main.py
function_overlays:
  "non.existent.function":
    description: "I shouldn't exist"
"""
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(manifest_yaml)

    # We expect this to fail or produce a diagnostic once implemented.
    # Currently ToolManifest doesn't even have function_overlays,
    # so load_manifest_file might fail during Pydantic validation
    # if it doesn't allow extra fields, or just ignore it.

    manifest, diag = load_manifest_file(manifest_path)

    # If Pydantic fails validation due to unknown field 'function_overlays' (if extra='forbid')
    # then manifest will be None and diag.errors will have the error.
    # If it ignores it, we need to assert it's NOT ignored and validated.

    if manifest is not None:
        # If it loaded, we check if validation logic (to be implemented) caught it
        # Since it's not implemented, this should fail.
        assert diag is not None, "Should have a diagnostic for invalid overlay fn_id"
    else:
        # If it failed to load, it might be due to missing 'function_overlays' field in model
        assert diag is not None
        assert any(
            "function_overlays" in err or "non.existent.function" in err for err in diag.errors
        )
