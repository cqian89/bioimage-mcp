import sys
from unittest.mock import MagicMock, patch

# Mock cellpose before importing the adapter if not present
try:
    import cellpose  # noqa: F401
except ImportError:
    mock_cellpose = MagicMock()
    mock_cellpose_models = MagicMock()
    mock_cellpose.models = mock_cellpose_models
    sys.modules["cellpose"] = mock_cellpose
    sys.modules["cellpose.models"] = mock_cellpose_models

    # Mock CellposeModel.eval for introspection
    def mock_eval(self, x, diameter=30.0, channels=None):
        """Mock eval function for introspection."""
        pass

    mock_cellpose_models.CellposeModel.eval = mock_eval

from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_cellpose_adapter_registered():
    """Cellpose adapter is registered."""
    # We mocked it above if it was missing, so it should be registered now
    # but wait, the registration happened when bioimage_mcp.registry.dynamic.adapters was imported
    # if it was imported before we mocked cellpose, it might not be there.
    # So we force re-population for the test.
    from bioimage_mcp.registry.dynamic.adapters import _populate_default_adapters

    # Reset registry to force re-population
    ADAPTER_REGISTRY.clear()
    _populate_default_adapters()

    assert "cellpose" in ADAPTER_REGISTRY


def test_cellpose_adapter_discover():
    """CellposeAdapter discovers eval function."""
    from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

    adapter = CellposeAdapter()

    # We need to make sure CellposeModel is not None in the adapter
    with patch("bioimage_mcp.registry.dynamic.adapters.cellpose.CellposeModel") as mock_model:
        mock_model.eval = lambda self, x: None
        mock_model.eval.__doc__ = "Segment cells."
        mock_model.eval.__name__ = "eval"
        mock_model.eval.__module__ = "cellpose.models"

        discovered = adapter.discover({"module_name": "cellpose.models"})

        assert len(discovered) > 0
        fn_ids = [m.fn_id for m in discovered]
        assert "cellpose.models.CellposeModel.eval" in fn_ids

        # Check that eval function has correct metadata
        eval_meta = next(m for m in discovered if m.fn_id == "cellpose.models.CellposeModel.eval")
        assert eval_meta.io_pattern == IOPattern.IMAGE_TO_LABELS
        assert "model_type" in eval_meta.parameters


def test_cellpose_adapter_io_pattern():
    """eval maps to IMAGE_TO_LABELS pattern."""
    from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

    adapter = CellposeAdapter()
    pattern = adapter.resolve_io_pattern("eval", None)
    assert pattern == IOPattern.IMAGE_TO_LABELS


def test_cellpose_adapter_dimension_hints():
    """eval returns appropriate dimension hints."""
    from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

    adapter = CellposeAdapter()
    hints = adapter.generate_dimension_hints("cellpose.models", "eval")

    assert hints is not None
    assert hints.min_ndim == 2
    assert hints.max_ndim == 3
    assert "Y" in hints.expected_axes
    assert "X" in hints.expected_axes


def test_cellpose_adapter_execute_logic():
    """Test execute logic by mocking run_segment."""
    from bioimage_mcp.artifacts.base import Artifact
    from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

    adapter = CellposeAdapter()

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
