import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock cellpose before importing the adapter if not present
try:
    import cellpose  # noqa: F401
except ImportError:
    mock_cellpose = MagicMock()
    mock_cellpose_models = MagicMock()
    mock_cellpose_train = MagicMock()
    mock_cellpose.models = mock_cellpose_models
    mock_cellpose.train = mock_cellpose_train
    sys.modules["cellpose"] = mock_cellpose
    sys.modules["cellpose.models"] = mock_cellpose_models
    sys.modules["cellpose.train"] = mock_cellpose_train

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

from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_cellpose_adapter_discovers_multiple_functions():
    """CellposeAdapter discovers eval and train_seg functions."""
    adapter = CellposeAdapter()

    # Test discovery for cellpose.models
    discovered = adapter.discover({"module_name": "cellpose.models.CellposeModel"})

    assert len(discovered) >= 1
    fn_ids = [m.fn_id for m in discovered]
    assert "cellpose.eval" in fn_ids

    # Check eval metadata
    eval_meta = next(m for m in discovered if m.fn_id == "cellpose.eval")
    assert eval_meta.io_pattern == IOPattern.IMAGE_TO_LABELS
    assert "diameter" in eval_meta.parameters
    assert "model_type" in eval_meta.parameters


def test_cellpose_adapter_discovers_train_seg():
    """CellposeAdapter discovers train_seg function."""
    adapter = CellposeAdapter()

    # Test discovery for cellpose.train
    discovered = adapter.discover({"module_name": "cellpose.train"})

    assert len(discovered) >= 1
    fn_ids = [m.fn_id for m in discovered]
    assert "cellpose.train_seg" in fn_ids

    # Check train_seg metadata
    train_meta = next(m for m in discovered if m.fn_id == "cellpose.train_seg")
    assert train_meta.io_pattern == IOPattern.TRAINING
    assert "n_epochs" in train_meta.parameters
    assert train_meta.parameters["n_epochs"].default == 500
    assert train_meta.parameters["n_epochs"].required is False
    assert train_meta.parameters["train_data"].required is True


def test_cellpose_adapter_backward_compatibility():
    """Existing cellpose.segment fn_id still works (mapped to eval)."""
    adapter = CellposeAdapter()

    discovered = adapter.discover({"module_name": "cellpose.models.CellposeModel"})
    fn_ids = [m.fn_id for m in discovered]
    assert "cellpose.segment" in fn_ids

    segment_meta = next(m for m in discovered if m.fn_id == "cellpose.segment")
    assert segment_meta.io_pattern == IOPattern.IMAGE_TO_LABELS
    assert "diameter" in segment_meta.parameters
    assert "model_type" in segment_meta.parameters
