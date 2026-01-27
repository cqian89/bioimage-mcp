import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from bioio_ome_zarr.writers import OMEZarrWriter


class TestOmeZarrDimsRoundtrip:
    """Integration tests for OME-Zarr dims round-trip through load()."""

    @pytest.fixture(autouse=True)
    def setup_path(self, tmp_path):
        """Add tools/base to path and configure allowlist."""
        # Add tools/base to path so we can import bioimage_mcp_base
        base_tools_path = str(Path(__file__).parents[2] / "tools" / "base")
        if base_tools_path not in sys.path:
            sys.path.insert(0, base_tools_path)

        # Configure allowlist for reading from tmp_path
        os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps([str(tmp_path)])
        yield
        # No specific cleanup needed as tmp_path is managed by pytest

    def test_load_ome_zarr_with_yxb_dims(self, tmp_path):
        """Loading OME-Zarr with YXB dims should preserve them."""
        from bioimage_mcp_base.ops.io import load

        zarr_path = tmp_path / "test_data.ome.zarr"

        # Create test data (Y=32, X=32, B=64 for microtime bins)
        data = np.random.randint(0, 100, (32, 32, 64), dtype=np.uint16)

        writer = OMEZarrWriter(
            store=str(zarr_path),
            level_shapes=[data.shape],
            dtype=data.dtype,
            axes_names=["y", "x", "b"],  # lowercase, bioio will uppercase
            axes_types=["space", "space", "other"],
            zarr_format=2,
        )
        writer.write_full_volume(data)

        result = load(inputs={}, params={"path": str(zarr_path)}, work_dir=tmp_path)

        image_ref = result["outputs"]["image"]
        assert image_ref["format"] == "OME-Zarr"
        # BioIO should uppercase them to YXB
        assert image_ref["dims"] == ["Y", "X", "B"]
        assert image_ref["metadata"]["dims"] == ["Y", "X", "B"]
        assert image_ref["metadata"]["shape"] == [32, 32, 64]

    def test_load_ome_zarr_reports_correct_format(self, tmp_path):
        """Loading OME-Zarr should report format='OME-Zarr'."""
        from bioimage_mcp_base.ops.io import load

        zarr_path = tmp_path / "simple.zarr"
        zarr_path.mkdir()

        # We need actual zarr data for BioImage to not fail
        data = np.zeros((10, 10), dtype=np.uint8)
        writer = OMEZarrWriter(
            store=str(zarr_path),
            level_shapes=[data.shape],
            dtype=data.dtype,
            axes_names=["y", "x"],
            axes_types=["space", "space"],
            zarr_format=2,
        )
        writer.write_full_volume(data)

        result = load(inputs={}, params={"path": str(zarr_path)}, work_dir=tmp_path)

        image_ref = result["outputs"]["image"]
        assert image_ref["format"] == "OME-Zarr"
