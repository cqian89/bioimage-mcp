from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import load_manifest_file


@pytest.mark.unit
def test_trackpy_manifest_is_valid() -> None:
    """Verify that the trackpy manifest is valid and discoverable."""
    # Find the real manifest file
    manifest_path = (
        Path(__file__).resolve().parent.parent.parent.parent / "tools" / "trackpy" / "manifest.yaml"
    )

    assert manifest_path.exists(), f"Manifest not found at {manifest_path}"

    manifest, diagnostic = load_manifest_file(manifest_path)

    if diagnostic and diagnostic.errors:
        pytest.fail(f"Manifest validation failed with errors: {diagnostic.errors}")

    # Note: Discovery will fail (generating a warning) until TrackpyAdapter is implemented in 05-02
    assert manifest is not None
    assert manifest.tool_id == "tools.trackpy"
    assert manifest.env_id == "bioimage-mcp-trackpy"
    assert manifest.entrypoint == "bioimage_mcp_trackpy/entrypoint.py"
    assert isinstance(manifest.dynamic_sources, list)
    assert len(manifest.dynamic_sources) == 1
    assert manifest.dynamic_sources[0].prefix == "trackpy"

    # Verify entrypoint exists relative to manifest
    entrypoint_path = manifest_path.parent / manifest.entrypoint
    assert entrypoint_path.exists(), f"Entrypoint not found at {entrypoint_path}"
