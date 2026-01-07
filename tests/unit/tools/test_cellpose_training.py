"""Unit tests for Cellpose training parameter schema (T028)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def cellpose_entrypoint():
    """Load the cellpose entrypoint module with mocked cellpose."""
    entrypoint_path = (
        Path(__file__).resolve().parents[3]
        / "tools"
        / "cellpose"
        / "bioimage_mcp_cellpose"
        / "entrypoint.py"
    )

    # Mock cellpose before importing entrypoint
    mock_cellpose = MagicMock()
    mock_cellpose.__version__ = "3.1.0"

    # Also mock submodules that entrypoint might import
    mock_train = MagicMock()
    mock_models = MagicMock()
    mock_cellpose.train = mock_train
    mock_cellpose.models = mock_models

    # Define a mock for cellpose.train.train_seg so signature introspection works
    def dummy_train_seg(
        train_data,
        train_labels,
        test_data=None,
        test_labels=None,
        n_epochs=10,
        learning_rate=0.1,
        weight_decay=0.0001,
        batch_size=8,
    ):
        pass

    mock_train.train_seg = dummy_train_seg

    # Define a mock for CellposeModel.eval
    class MockCellposeModel:
        def eval(self, x, batch_size=8, channels=None, channel_axis=None, z_axis=None):
            pass

    mock_models.CellposeModel = MockCellposeModel

    with patch.dict(
        sys.modules,
        {
            "cellpose": mock_cellpose,
            "cellpose.train": mock_train,
            "cellpose.models": mock_models,
        },
    ):
        spec = importlib.util.spec_from_file_location("cellpose_entrypoint", entrypoint_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load entrypoint from {entrypoint_path}")

        module = importlib.util.module_from_spec(spec)

        # Mocking environment for initialization
        os.environ["BIOIMAGE_MCP_SESSION_ID"] = "test-session"
        os.environ["BIOIMAGE_MCP_ENV_ID"] = "bioimage-mcp-cellpose"

        spec.loader.exec_module(module)
        module._initialize_worker("test-session", "bioimage-mcp-cellpose")
        yield module


def test_train_seg_params_schema_has_required_fields(cellpose_entrypoint) -> None:
    """T028: Test that cellpose.train.train_seg schema includes expected parameters."""
    ep = cellpose_entrypoint

    # This should fail initially because handle_meta_describe doesn't support cellpose.train.train_seg yet
    # or _introspect_cellpose_train is not implemented.

    params = {"target_fn": "cellpose.train.train_seg"}
    response = ep.handle_meta_describe(params)

    assert response["ok"] is True, f"handle_meta_describe failed: {response.get('error')}"

    result = response["result"]
    assert "params_schema" in result
    schema = result["params_schema"]

    properties = schema.get("properties", {})
    assert "n_epochs" in properties
    assert "learning_rate" in properties
    assert "weight_decay" in properties
    assert "batch_size" in properties


def test_train_seg_inputs_schema(cellpose_entrypoint) -> None:
    """T028: Test that cellpose.train.train_seg schema includes required inputs."""
    ep = cellpose_entrypoint

    # Assuming we might add input schema to meta.describe result
    # or checking if the implementation expects these inputs.

    params = {"target_fn": "cellpose.train.train_seg"}
    response = ep.handle_meta_describe(params)

    assert response["ok"] is True
    result = response["result"]

    # The requirement says "Test required inputs (images, labels)"
    # Some tools might put inputs in the schema as well, or we check a separate 'inputs_schema'
    # if our contract supports it. Current handle_meta_describe only returns 'params_schema'.

    assert "inputs_schema" in result
    inputs_properties = result["inputs_schema"].get("properties", {})
    assert "images" in inputs_properties
    assert "labels" in inputs_properties
