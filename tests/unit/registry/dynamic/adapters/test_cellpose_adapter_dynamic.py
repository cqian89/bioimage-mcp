import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from bioimage_mcp.registry.dynamic.models import IOPattern


@pytest.fixture(scope="function")
def adapter():
    """Setup adapter with mocked cellpose environment."""
    # Create mocks
    mock_cellpose = MagicMock()
    mock_cellpose_models = MagicMock()
    mock_cellpose_train = MagicMock()

    # Make sure submodules are accessible via attributes
    mock_cellpose.models = mock_cellpose_models
    mock_cellpose.train = mock_cellpose_train

    # Mock CellposeModel.eval for introspection
    def mock_eval(self, x, diameter=30.0, channels=None):
        """Mock eval function for segmentation."""
        pass

    mock_cellpose_models.CellposeModel.eval = mock_eval

    # Mock train_seg for introspection
    def mock_train_seg(train_data, train_labels, test_data=None, test_labels=None, n_epochs=500):
        """Mock train_seg function for training."""
        pass

    mock_cellpose_train.train_seg = mock_train_seg

    # Patch sys.modules
    # We use patch.dict to safely inject mocks and clean them up afterwards
    with patch.dict(
        sys.modules,
        {
            "cellpose": mock_cellpose,
            "cellpose.models": mock_cellpose_models,
            "cellpose.train": mock_cellpose_train,
        },
    ):
        # Import and reload the adapter to ensure it picks up the mocked modules
        import bioimage_mcp.registry.dynamic.adapters.cellpose

        importlib.reload(bioimage_mcp.registry.dynamic.adapters.cellpose)

        from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

        yield CellposeAdapter()

    # After test, we should reload again to clear any stale state if needed,
    # but patch.dict handles sys.modules cleanup.
    # However, the module object itself (bioimage_mcp.registry.dynamic.adapters.cellpose)
    # might still hold references to the mocks if we don't reload it again.
    # Ideally, we reload it here too, but it might fail if cellpose is missing.
    # That's fine for subsequent tests that expect cellpose to be missing.
    import bioimage_mcp.registry.dynamic.adapters.cellpose

    importlib.reload(bioimage_mcp.registry.dynamic.adapters.cellpose)


def test_cellpose_adapter_discovers_multiple_functions(adapter):
    """CellposeAdapter discovers eval and train_seg functions."""
    # Test discovery for cellpose.models
    discovered = adapter.discover({"module_name": "cellpose.models.CellposeModel"})

    assert len(discovered) >= 1
    fn_ids = [m.fn_id for m in discovered]
    assert "cellpose.models.CellposeModel.eval" in fn_ids

    # Check eval metadata
    eval_meta = next(m for m in discovered if m.fn_id == "cellpose.models.CellposeModel.eval")
    assert eval_meta.io_pattern == IOPattern.IMAGE_TO_LABELS
    assert "diameter" in eval_meta.parameters
    assert "model_type" in eval_meta.parameters


def test_cellpose_adapter_discovers_train_seg(adapter):
    """CellposeAdapter discovers train_seg function."""
    # Test discovery for cellpose.train
    discovered = adapter.discover({"module_name": "cellpose.train"})

    assert len(discovered) >= 1
    fn_ids = [m.fn_id for m in discovered]
    assert "cellpose.train.train_seg" in fn_ids

    # Check train_seg metadata
    train_meta = next(m for m in discovered if m.fn_id == "cellpose.train.train_seg")
    assert train_meta.io_pattern == IOPattern.TRAINING
    assert "n_epochs" in train_meta.parameters
    assert train_meta.parameters["n_epochs"].default == 500
    assert train_meta.parameters["n_epochs"].required is False
    assert train_meta.parameters["train_data"].required is True


def test_cellpose_adapter_execute(adapter):
    """CellposeAdapter can execute eval."""
    from bioimage_mcp.artifacts.base import Artifact

    # Mock run_segment
    mock_result = {
        "labels": {"type": "LabelImageRef", "uri": "file:///tmp/labels.tif"},
        "cellpose_bundle": {"type": "NativeOutputRef", "uri": "file:///tmp/bundle.npy"},
    }

    # Create a mock artifact
    mock_input = MagicMock(spec=Artifact)
    mock_input.model_dump.return_value = {"uri": "file:///tmp/input.tif"}

    # Mock the entire bioimage_mcp_cellpose module structure
    mock_run_eval = MagicMock(return_value=mock_result)
    mock_ops = MagicMock()
    mock_ops.run_segment = mock_run_eval

    with patch.dict(
        sys.modules,
        {
            "bioimage_mcp_cellpose": MagicMock(),
            "bioimage_mcp_cellpose.ops": MagicMock(),
            "bioimage_mcp_cellpose.ops.segment": mock_ops,
        },
    ):
        outputs = adapter.execute(
            "cellpose.models.CellposeModel.eval", [mock_input], {"diameter": 30}
        )

        assert len(outputs) == 2
        assert outputs[0]["type"] == "LabelImageRef"
        assert outputs[1]["type"] == "NativeOutputRef"
        mock_run_eval.assert_called_once()
