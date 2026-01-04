import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add tools/cellpose to sys.path
REPO_ROOT = Path(__file__).parent.parent.parent
TOOLS_CELLPOSE = REPO_ROOT / "tools" / "cellpose"
if str(TOOLS_CELLPOSE) not in sys.path:
    sys.path.insert(0, str(TOOLS_CELLPOSE))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioimage_mcp_cellpose.entrypoint import process_execute_request


def test_dynamic_dispatch_segment():
    request = {
        "command": "execute",
        "fn_id": "cellpose.segment",
        "inputs": {},
        "params": {},
        "work_dir": "/tmp/work_segment",
        "ordinal": 1,
    }
    mock_handle = MagicMock()
    mock_handle.return_value = {
        "ok": True,
        "outputs": {"labels": {"path": "foo", "type": "LabelImageRef", "format": "OME-TIFF"}},
    }
    with patch.dict(
        "bioimage_mcp_cellpose.entrypoint.FUNCTION_HANDLERS", {"cellpose.segment": mock_handle}
    ):
        response = process_execute_request(request)
        assert response["ok"] is True
        assert mock_handle.called


def test_dynamic_dispatch_eval():
    request = {
        "command": "execute",
        "fn_id": "cellpose.eval",
        "inputs": {},
        "params": {},
        "work_dir": "/tmp/work_eval",
        "ordinal": 1,
    }
    mock_handle = MagicMock()
    mock_handle.return_value = {
        "ok": True,
        "outputs": {"labels": {"path": "foo", "type": "LabelImageRef", "format": "OME-TIFF"}},
    }
    with patch.dict(
        "bioimage_mcp_cellpose.entrypoint.FUNCTION_HANDLERS", {"cellpose.eval": mock_handle}
    ):
        response = process_execute_request(request)
        assert response["ok"] is True
        assert mock_handle.called


def test_dynamic_dispatch_train_seg():
    request = {
        "command": "execute",
        "fn_id": "cellpose.train_seg",
        "inputs": {},
        "params": {},
        "work_dir": "/tmp/work_train",
        "ordinal": 1,
    }
    response = process_execute_request(request)
    assert response["ok"] is False
    assert "implemented" in response["error"]["message"].lower()
    assert "not" in response["error"]["message"].lower()


def test_dynamic_dispatch_unknown():
    request = {
        "command": "execute",
        "fn_id": "unknown",
        "inputs": {},
        "params": {},
        "work_dir": "/tmp/work_unknown",
        "ordinal": 1,
    }
    response = process_execute_request(request)
    assert response["ok"] is False
    assert "Unknown fn_id" in response["error"]["message"]


def test_meta_describe_eval():
    request = {
        "command": "execute",
        "fn_id": "meta.describe",
        "params": {"target_fn": "cellpose.eval"},
        "work_dir": "/tmp/work_meta",
        "ordinal": 1,
    }
    # Mock _introspect_cellpose_eval to avoid heavy imports
    with (
        patch("bioimage_mcp_cellpose.entrypoint._introspect_cellpose_eval") as mock_intro,
        patch("bioimage_mcp_cellpose.entrypoint._convert_memory_inputs_to_files") as mock_convert,
    ):
        mock_intro.return_value = {"type": "object", "properties": {}}
        mock_convert.side_effect = lambda inputs, wd: inputs

        response = process_execute_request(request)

        if not response.get("ok"):
            print(f"Response error: {response}")

        assert response["ok"] is True
        assert "result" in response["outputs"]
        assert response["outputs"]["result"]["params_schema"] == {
            "type": "object",
            "properties": {},
        }
