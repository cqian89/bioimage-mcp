# We need to import the functions from the entrypoint script.
# Since it's a script and might have side effects on import, we handle it carefully.
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

# Add tools/base to sys.path so we can import bioimage_mcp_base.entrypoint
TOOLS_BASE = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(TOOLS_BASE) not in sys.path:
    sys.path.insert(0, str(TOOLS_BASE))

from bioimage_mcp_base import entrypoint


def test_infer_dims_from_shape():
    # This function doesn't exist yet, so this test will fail during RED phase
    # if we try to call it. But wait, I'm supposed to write it in the GREEN phase.
    # For now, I'll test it via the side effects in other functions, or
    # if I want to test it directly I'll have to wait until it's defined.
    # Actually, the instructions say:
    # "Test _infer_dims_from_shape for 2D, 3D, 4D, 5D, and edge cases"

    assert hasattr(entrypoint, "_infer_dims_from_shape"), "_infer_dims_from_shape not implemented"

    assert entrypoint._infer_dims_from_shape((100, 100)) == "YX"
    assert entrypoint._infer_dims_from_shape((10, 100, 100)) == "ZYX"
    assert entrypoint._infer_dims_from_shape((3, 10, 100, 100)) == "CZYX"
    assert entrypoint._infer_dims_from_shape((1, 3, 10, 100, 100)) == "TCZYX"
    assert entrypoint._infer_dims_from_shape((5, 1, 3, 10, 100, 100)) == "TCZYX"
    # "For other dimensions, return last N characters of "TCZYX""
    # ndim=6 -> last 6 of "TCZYX" is "TCZYX" (if it handles >5 by capping or something)
    # The requirement says: "For other dimensions, return last N characters of "TCZYX""
    # If N=1, "X". If N=6, "TCZYX"?
    assert entrypoint._infer_dims_from_shape((100,)) == "X"


def test_convert_outputs_to_memory_dims(tmp_path):
    # Mock _SESSION_ID and _ENV_ID
    with (
        patch("bioimage_mcp_base.entrypoint._SESSION_ID", "test-session"),
        patch("bioimage_mcp_base.entrypoint._ENV_ID", "test-env"),
        patch("bioimage_mcp_base.entrypoint._load_input_data") as mock_load,
    ):
        # 2D data
        data_2d = np.zeros((100, 100))
        mock_load.return_value = data_2d

        # File path output
        temp_file = tmp_path / "test.tif"
        temp_file.touch()
        outputs = {"out": temp_file}

        mem_outputs = entrypoint._convert_outputs_to_memory(outputs, tmp_path)

        assert mem_outputs["out"]["metadata"]["dims"] == "YX"
        assert mem_outputs["out"]["metadata"]["shape"] == [100, 100]

        # 3D data
        data_3d = np.zeros((10, 100, 100))
        mock_load.return_value = data_3d
        temp_file_3d = tmp_path / "test3d.tif"
        temp_file_3d.touch()
        outputs = {"out": temp_file_3d}
        mem_outputs = entrypoint._convert_outputs_to_memory(outputs, tmp_path)
        assert mem_outputs["out"]["metadata"]["dims"] == "ZYX"


def test_process_execute_request_legacy_memory_dims():
    # Test the path around line 499
    with (
        patch("bioimage_mcp_base.entrypoint._SESSION_ID", "test-session"),
        patch("bioimage_mcp_base.entrypoint._ENV_ID", "test-env"),
        patch.dict(entrypoint.FN_MAP, {}, clear=False) as mock_fn_map,
        patch("bioimage_mcp_base.entrypoint._load_input_data") as mock_load,
    ):
        # Mock a function that returns a path (legacy behavior)
        mock_path = MagicMock(spec=Path)
        mock_path.unlink = MagicMock()
        mock_fn_map["base.some_fn"] = (lambda **kwargs: mock_path, {})

        # Mock loaded data to be 2D
        data_2d = np.zeros((100, 100))
        mock_load.return_value = data_2d

        request = {
            "id": "base.some_fn",
            "params": {"output_mode": "memory"},
            "inputs": {},
            "work_dir": "/tmp",
            "ordinal": 1,
        }

        response = entrypoint.process_execute_request(request)

        assert response["ok"] is True
        assert response["outputs"]["output"]["metadata"]["dims"] == "YX"
        assert response["outputs"]["output"]["metadata"]["shape"] == [100, 100]
