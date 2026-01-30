import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

# Add tools/base to sys.path so we can import bioimage_mcp_base.entrypoint
TOOLS_BASE = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(TOOLS_BASE) not in sys.path:
    sys.path.insert(0, str(TOOLS_BASE))

from bioimage_mcp_base import entrypoint  # noqa: E402


def test_expand_to_5d_exists():
    assert hasattr(entrypoint, "_expand_to_5d"), "_expand_to_5d not implemented"


def test_expand_to_5d_logic():
    # 1D
    data1d = np.zeros((10,))
    res1d = entrypoint._expand_to_5d(data1d)
    assert res1d.shape == (1, 1, 1, 1, 10)

    # 2D
    data2d = np.zeros((100, 100))
    res2d = entrypoint._expand_to_5d(data2d)
    assert res2d.shape == (1, 1, 1, 100, 100)

    # 3D
    data3d = np.zeros((10, 100, 100))
    res3d = entrypoint._expand_to_5d(data3d)
    assert res3d.shape == (1, 1, 10, 100, 100)

    # 4D
    data4d = np.zeros((3, 10, 100, 100))
    res4d = entrypoint._expand_to_5d(data4d)
    assert res4d.shape == (1, 3, 10, 100, 100)

    # 5D
    data5d = np.zeros((1, 3, 10, 100, 100))
    res5d = entrypoint._expand_to_5d(data5d)
    assert res5d.shape == (1, 3, 10, 100, 100)

    # 6D
    data6d = np.zeros((1, 1, 3, 10, 100, 100))
    res6d = entrypoint._expand_to_5d(data6d)
    assert res6d.shape == (1, 1, 3, 10, 100, 100)


def test_convert_memory_inputs_to_files_with_2d(tmp_path):
    mock_writer_cls = MagicMock()
    mock_writer_module = MagicMock()
    mock_writer_module.OMEZarrWriter = mock_writer_cls
    with (
        patch("bioimage_mcp_base.entrypoint._load_from_memory") as mock_load,
        patch.dict(sys.modules, {"bioio_ome_zarr.writers": mock_writer_module}),
    ):
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer
        data_2d = np.zeros((100, 100))
        mock_load.return_value = data_2d

        inputs = {"image": {"uri": "mem://test-session/test-env/art1", "type": "BioImageRef"}}

        entrypoint._convert_memory_inputs_to_files(inputs, tmp_path)

        # Verify OMEZarrWriter.write_full_volume was called with 2D data
        assert mock_writer.write_full_volume.called
        args, _ = mock_writer.write_full_volume.call_args
        saved_data = args[0]
        assert saved_data.ndim == 2
        assert saved_data.shape == (100, 100)


def test_handle_materialize_with_2d():
    with (
        patch("bioimage_mcp_base.entrypoint._MEMORY_ARTIFACTS", {}),
        patch("bioio.writers.OmeTiffWriter.save") as mock_save,
    ):
        data_2d = np.zeros((100, 100))
        entrypoint._MEMORY_ARTIFACTS["art1"] = data_2d

        request = {
            "ref_id": "mem://test-session/test-env/art1",
            "target_format": "OME-TIFF",
            "dest_path": "/tmp/test.ome.tif",
            "ordinal": 1,
        }

        # We need to mock _SESSION_ID and _ENV_ID because _extract_artifact_id
        # might use them or at least we need to be careful.
        # Actually _extract_artifact_id just parses the URI.

        entrypoint.handle_materialize(request)

        # Verify OmeTiffWriter.save was called with 2D data
        assert mock_save.called
        args, _ = mock_save.call_args
        saved_data = args[0]
        assert saved_data.ndim == 2
        assert saved_data.shape == (100, 100)


def test_handle_materialize_ome_zarr_with_2d():
    mock_writer_cls = MagicMock()
    mock_writer_module = MagicMock()
    mock_writer_module.OMEZarrWriter = mock_writer_cls

    with (
        patch.dict(sys.modules, {"bioio_ome_zarr.writers": mock_writer_module}),
        patch("bioimage_mcp_base.entrypoint._MEMORY_ARTIFACTS", {}),
    ):
        data_2d = np.zeros((100, 100))
        entrypoint._MEMORY_ARTIFACTS["art1"] = data_2d

        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        request = {
            "ref_id": "mem://test-session/test-env/art1",
            "target_format": "OME-Zarr",
            "dest_path": "/tmp/test.ome.zarr",
            "ordinal": 1,
        }

        entrypoint.handle_materialize(request)

        # Verify OMEZarrWriter was initialized with 2D shape and correct axes
        assert mock_writer_cls.called
        kwargs = mock_writer_cls.call_args.kwargs
        assert kwargs["level_shapes"] == [(100, 100)]
        assert kwargs["axes_names"] == ["y", "x"]
        assert kwargs["axes_types"] == ["space", "space"]

        # Verify write_full_volume was called with 2D data
        assert mock_writer.write_full_volume.called
        args, _ = mock_writer.write_full_volume.call_args
        saved_data = args[0]
        assert saved_data.ndim == 2
        assert saved_data.shape == (100, 100)
