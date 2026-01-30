from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the tool pack directory to sys.path so we can import the entrypoint
# The structure is tools/cellpose/bioimage_mcp_cellpose/entrypoint.py
REPO_ROOT = Path(__file__).parent.parent.parent.parent
TOOL_DIR = REPO_ROOT / "tools" / "cellpose"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

# Mock numpy as it's a top-level import in entrypoint.py
with patch("numpy.ndarray", MagicMock):
    import bioimage_mcp_cellpose.entrypoint as entrypoint


@pytest.fixture
def mock_meta_context():
    """Mock the introspection and version helpers to be deterministic."""
    with (
        patch("bioimage_mcp_cellpose.entrypoint._introspect_cellpose_fn") as mock_introspect,
        patch("bioimage_mcp_cellpose.entrypoint._get_cellpose_version") as mock_version,
    ):
        mock_introspect.return_value = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
            "required": [],
        }
        mock_version.return_value = "3.4.5"
        yield mock_introspect, mock_version


def test_handle_meta_describe_success(mock_meta_context):
    """Test successful meta.describe response shape."""
    params = {"target_fn": "cellpose.models.CellposeModel.eval"}
    response = entrypoint.handle_meta_describe(params)

    assert response["ok"] is True
    assert "result" in response
    result = response["result"]
    assert result["params_schema"] == {
        "type": "object",
        "properties": {"test": {"type": "string"}},
        "required": [],
    }
    assert result["tool_version"] == "3.4.5"
    assert result["introspection_source"] == "python_api"


def test_handle_meta_describe_missing_params():
    """Test meta.describe error handling for missing target_fn."""
    response = entrypoint.handle_meta_describe({})
    assert response["ok"] is False
    assert isinstance(response["error"], str)
    assert "Missing" in response["error"]


def test_handle_meta_describe_unknown_fn(mock_meta_context):
    """Test meta.describe error handling for unknown function."""
    response = entrypoint.handle_meta_describe({"target_fn": "non.existent.fn"})
    assert response["ok"] is False
    assert isinstance(response["error"], str)
    assert "Unknown" in response["error"]


def test_handle_meta_list_shape(mock_meta_context):
    """Test meta.list response shape and entry richness."""
    # handle_meta_list(inputs, params, work_dir)
    response = entrypoint.handle_meta_list({}, {}, Path("/tmp"))

    assert response["ok"] is True
    assert "result" in response
    result = response["result"]
    assert "functions" in result
    assert result["tool_version"] == "3.4.5"
    assert result["introspection_source"] == "manual"

    functions = result["functions"]
    assert len(functions) > 0

    # Check a constructor entry
    model_init = next(f for f in functions if f["id"] == "cellpose.models.CellposeModel")
    assert model_init["module"] == "cellpose.models"
    assert model_init["io_pattern"] == "pure_constructor"
    assert "name" in model_init
    assert "summary" in model_init

    # Check a generic entry
    model_eval = next(f for f in functions if f["id"] == "cellpose.models.CellposeModel.eval")
    assert model_eval["module"] == "cellpose.models"
    assert model_eval["io_pattern"] == "generic"

    # Check a training entry
    train_seg = next(f for f in functions if f["id"] == "cellpose.train.train_seg")
    assert train_seg["module"] == "cellpose.train"
    assert train_seg["io_pattern"] == "training"
