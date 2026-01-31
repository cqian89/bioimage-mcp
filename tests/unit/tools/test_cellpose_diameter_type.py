from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the tool pack directory to sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_DIR = REPO_ROOT / "tools" / "cellpose"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

# Mock heavy dependencies before importing entrypoint
sys.modules["cellpose"] = MagicMock()
sys.modules["cellpose.models"] = MagicMock()
sys.modules["cellpose.train"] = MagicMock()
sys.modules["cellpose.denoise"] = MagicMock()
sys.modules["cellpose.metrics"] = MagicMock()
sys.modules["bioio"] = MagicMock()

import bioimage_mcp_cellpose.entrypoint as entrypoint  # noqa: E402


def test_cellpose_diameter_is_number():
    """Verify that diameter is correctly typed as number in CellposeModel.eval.

    This ensures that even if introspection falls back to 'string' due to
    a None default, the curated parameters override it to 'number'.
    """

    # Mock signature where diameter has a None default (common in Cellpose)
    mock_param = MagicMock()
    mock_param.name = "diameter"
    mock_param.default = None
    mock_param.kind = 1  # POSITIONAL_OR_KEYWORD

    mock_sig = MagicMock()
    mock_sig.parameters = {"diameter": mock_param}

    with patch("inspect.signature", return_value=mock_sig):
        schema = entrypoint._introspect_cellpose_fn("cellpose.models.CellposeModel.eval")

        assert "diameter" in schema["properties"]
        assert schema["properties"]["diameter"]["type"] == "number"
        assert schema["properties"]["diameter"]["default"] == 30.0
        assert "Estimated cell diameter" in schema["properties"]["diameter"]["description"]


def test_cellpose_other_curated_params():
    """Verify other curated parameters are also correctly set."""
    mock_sig = MagicMock()
    mock_sig.parameters = {}  # Empty signature to test curation override

    with patch("inspect.signature", return_value=mock_sig):
        schema = entrypoint._introspect_cellpose_fn("cellpose.models.CellposeModel.eval")

        assert schema["properties"]["model_type"]["type"] == "string"
        assert schema["properties"]["channels"]["type"] == "array"
        assert schema["properties"]["flow_threshold"]["type"] == "number"
        assert schema["properties"]["cellprob_threshold"]["type"] == "number"
        assert schema["properties"]["tile"]["type"] == "boolean"
        assert schema["properties"]["diameter"]["type"] == "number"
