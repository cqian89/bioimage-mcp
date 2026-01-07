from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

# Add tools/base to sys.path
TOOLS_BASE = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(TOOLS_BASE) not in sys.path:
    sys.path.insert(0, str(TOOLS_BASE))

from bioimage_mcp_base.ops.io import export  # noqa: E402


def test_export_2d_to_ome_zarr_preserves_dims(tmp_path):
    # Mock 2D data
    data_2d = np.zeros((100, 120), dtype=np.uint8)

    # Mock bioio_ome_zarr writer
    mock_writer_cls = MagicMock()
    mock_writer_module = MagicMock()
    mock_writer_module.OMEZarrWriter = mock_writer_cls

    # Mock load_native_image to return 2D data
    with (
        patch("bioimage_mcp_base.ops.io.load_native_image") as mock_load,
        patch.dict(sys.modules, {"bioio_ome_zarr.writers": mock_writer_module}),
        patch.dict(os.environ, {"BIOIMAGE_MCP_FS_ALLOWLIST_WRITE": json.dumps([str(tmp_path)])}),
    ):
        mock_load.return_value = data_2d
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        inputs = {
            "image": {
                "uri": "file:///tmp/test.tif",
                "type": "BioImageRef",
                "metadata": {"dims": ["Y", "X"]},
            }
        }
        params = {"format": "OME-ZARR", "path": str(tmp_path / "out.ome.zarr")}
        work_dir = tmp_path

        export(inputs=inputs, params=params, work_dir=work_dir)

        # Verify OMEZarrWriter was initialized with 2D shape and axes
        assert mock_writer_cls.called
        kwargs = mock_writer_cls.call_args.kwargs
        assert kwargs["level_shapes"] == [(100, 120)]
        assert kwargs["axes_names"] == ["y", "x"]

        # Verify write_full_volume was called with 2D data
        assert mock_writer.write_full_volume.called
        args, _ = mock_writer.write_full_volume.call_args
        saved_data = args[0]
        assert saved_data.shape == (100, 120)
        assert saved_data.ndim == 2


def test_export_3d_to_ome_zarr_preserves_dims(tmp_path):
    # Mock 3D data (Z, Y, X)
    data_3d = np.zeros((10, 100, 120), dtype=np.uint16)

    # Mock bioio_ome_zarr writer
    mock_writer_cls = MagicMock()
    mock_writer_module = MagicMock()
    mock_writer_module.OMEZarrWriter = mock_writer_cls

    # Mock load_native_image to return 3D data
    with (
        patch("bioimage_mcp_base.ops.io.load_native_image") as mock_load,
        patch.dict(sys.modules, {"bioio_ome_zarr.writers": mock_writer_module}),
        patch.dict(os.environ, {"BIOIMAGE_MCP_FS_ALLOWLIST_WRITE": json.dumps([str(tmp_path)])}),
    ):
        mock_load.return_value = data_3d
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        inputs = {
            "image": {
                "uri": "file:///tmp/test.tif",
                "type": "BioImageRef",
                "metadata": {"dims": ["Z", "Y", "X"]},
            }
        }
        params = {"format": "OME-ZARR", "path": str(tmp_path / "out.ome.zarr")}
        work_dir = tmp_path

        export(inputs=inputs, params=params, work_dir=work_dir)

        # Verify OMEZarrWriter was initialized with 3D shape and axes
        assert mock_writer_cls.called
        kwargs = mock_writer_cls.call_args.kwargs
        assert kwargs["level_shapes"] == [(10, 100, 120)]
        assert kwargs["axes_names"] == ["z", "y", "x"]

        # Verify write_full_volume was called with 3D data
        assert mock_writer.write_full_volume.called
        args, _ = mock_writer.write_full_volume.call_args
        saved_data = args[0]
        assert saved_data.shape == (10, 100, 120)
        assert saved_data.ndim == 3


def test_export_2d_to_ome_zarr_no_metadata_dims(tmp_path):
    # Mock 2D data
    data_2d = np.zeros((100, 120), dtype=np.uint8)

    # Mock bioio_ome_zarr writer
    mock_writer_cls = MagicMock()
    mock_writer_module = MagicMock()
    mock_writer_module.OMEZarrWriter = mock_writer_cls

    # Mock load_native_image to return 2D data
    with (
        patch("bioimage_mcp_base.ops.io.load_native_image") as mock_load,
        patch.dict(sys.modules, {"bioio_ome_zarr.writers": mock_writer_module}),
        patch.dict(os.environ, {"BIOIMAGE_MCP_FS_ALLOWLIST_WRITE": json.dumps([str(tmp_path)])}),
    ):
        mock_load.return_value = data_2d
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        inputs = {
            "image": {
                "uri": "file:///tmp/test.tif",
                "type": "BioImageRef",
                "metadata": {},  # No dims
            }
        }
        params = {"format": "OME-ZARR", "path": str(tmp_path / "out.ome.zarr")}
        work_dir = tmp_path

        export(inputs=inputs, params=params, work_dir=work_dir)

        # Verify OMEZarrWriter was initialized with inferred 2D axes
        assert mock_writer_cls.called
        kwargs = mock_writer_cls.call_args.kwargs
        assert kwargs["level_shapes"] == [(100, 120)]
        assert kwargs["axes_names"] == ["y", "x"]


def test_export_ome_zarr_squeezes_singletons_to_match_dims(tmp_path):
    """_export_ome_zarr should squeeze singleton dims to match provided dims list."""
    import numpy as np
    from bioimage_mcp_base.ops.io import _export_ome_zarr as export_ome_zarr

    # 5D data with singletons: (1, 1, 1, 64, 64) - effectively 2D
    data = np.random.rand(1, 1, 1, 64, 64).astype(np.float32)
    dims = ["Y", "X"]  # 2D dims

    out_path = tmp_path / "test_squeeze.ome.zarr"

    # Should not raise - function should squeeze to match dims
    export_ome_zarr(data, out_path, dims=dims)

    assert out_path.exists()
