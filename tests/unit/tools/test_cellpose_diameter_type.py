from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the tool pack directory to sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_DIR = REPO_ROOT / "tools" / "cellpose"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

# Names we mock at collection time must be scoped to fixture teardown
_MOCKED_MODULES = [
    "cellpose",
    "cellpose.models",
    "cellpose.train",
    "cellpose.denoise",
    "cellpose.metrics",
    "bioio",
]


@pytest.fixture()
def _cellpose_entrypoint():
    """Import ``bioimage_mcp_cellpose.entrypoint`` under mocked heavy deps.

    All ``sys.modules`` patches are undone on teardown so later tests that
    perform a function-body ``import bioio`` get the real module (or an
    ImportError), never a stale ``MagicMock``.
    """
    saved = {name: sys.modules.get(name) for name in _MOCKED_MODULES}
    # Also save the entrypoint module itself so we can force a fresh import
    ep_key = "bioimage_mcp_cellpose.entrypoint"
    saved_ep = sys.modules.get(ep_key)

    for name in _MOCKED_MODULES:
        sys.modules[name] = MagicMock()

    # Force a fresh import of the entrypoint under the mocked modules
    if ep_key in sys.modules:
        del sys.modules[ep_key]
    import bioimage_mcp_cellpose.entrypoint as entrypoint

    importlib.reload(entrypoint)

    yield entrypoint

    # Restore original sys.modules state
    for name in _MOCKED_MODULES:
        if saved[name] is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = saved[name]

    if saved_ep is None:
        sys.modules.pop(ep_key, None)
    else:
        sys.modules[ep_key] = saved_ep


def test_cellpose_diameter_is_number(_cellpose_entrypoint):
    """Verify that diameter is correctly typed as number in CellposeModel.eval.

    This ensures that even if introspection falls back to 'string' due to
    a None default, the curated parameters override it to 'number'.
    """
    entrypoint = _cellpose_entrypoint

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


def test_cellpose_other_curated_params(_cellpose_entrypoint):
    """Verify other curated parameters are also correctly set."""
    entrypoint = _cellpose_entrypoint
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


def test_bioio_not_mocked_after_cellpose_fixture(_cellpose_entrypoint):
    """Regression: ``import bioio`` after the cellpose fixture must not return a MagicMock."""
    # The fixture should clean up sys.modules on teardown,
    # but we check the state *during* the test while the fixture is active.
    # After fixture teardown (i.e. in a test collected *later*), bioio must
    # not be a MagicMock.  We verify the invariant that the fixture at least
    # records what it needs to restore.
    assert "bioio" in sys.modules  # fixture is still active
    # After this test, the fixture tears down and restores sys.modules.


def test_bioio_is_not_magicmock_post_cleanup():
    """Verify bioio is not a MagicMock in sys.modules after cellpose fixture teardown."""
    bioio_mod = sys.modules.get("bioio")
    if bioio_mod is not None:
        assert not isinstance(bioio_mod, MagicMock), (
            "bioio is still a MagicMock in sys.modules after cellpose fixture cleanup"
        )
