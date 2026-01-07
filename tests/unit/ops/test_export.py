from __future__ import annotations

from unittest.mock import MagicMock

from bioimage_mcp.artifacts.export import export_artifact


def test_export_respects_explicit_format(tmp_path):
    """T032: export_artifact respects explicit format parameter."""
    store = MagicMock()
    ref_id = "test-ref"
    dest_path = tmp_path / "output.ome.tiff"

    # We expect the export function to take a format parameter
    # This should fail initially because the function doesn't accept 'format' yet
    export_artifact(store, ref_id=ref_id, dest_path=dest_path, format="OME-TIFF")

    store.export.assert_called_once_with(ref_id, dest_path=dest_path, format="OME-TIFF")
