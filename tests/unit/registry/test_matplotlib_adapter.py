import pytest
from unittest.mock import patch, MagicMock

# Note: These imports will fail until the implementation is added (TDD RED phase)
try:
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
except ImportError:
    MatplotlibAdapter = None


@pytest.fixture
def adapter():
    if MatplotlibAdapter is None:
        pytest.fail("MatplotlibAdapter not implemented yet")
    return MatplotlibAdapter()


def test_agg_backend_enforced():
    """
    T007: Test that the adapter enforces the 'Agg' backend on initialization.
    """
    if MatplotlibAdapter is None:
        pytest.fail("MatplotlibAdapter not implemented yet")

    # We patch matplotlib.use before importing/initializing the adapter
    # if it hasn't been done yet, or just check if it was called.
    with patch("matplotlib.use") as mock_use:
        _ = MatplotlibAdapter()
        # The adapter should call matplotlib.use('Agg')
        mock_use.assert_called_once_with("Agg")


def test_interactive_methods_blocked(adapter):
    """
    T007: Test that interactive methods like show, pause, ginput, connect are blocked.
    """
    interactive_methods = [
        "base.matplotlib.pyplot.show",
        "base.matplotlib.pyplot.pause",
        "base.matplotlib.pyplot.ginput",
        "base.matplotlib.pyplot.connect",
    ]

    for fn_id in interactive_methods:
        with pytest.raises(ValueError, match="(?i)blocked|denied|not allowed|forbidden"):
            adapter.execute(fn_id, inputs={}, params={})


def test_unknown_function_rejected(adapter):
    """
    T007: Test that unknown/non-allowlisted functions are rejected.
    """
    with pytest.raises(ValueError, match="(?i)unknown|not allowed|forbidden"):
        adapter.execute("base.matplotlib.pyplot.some_random_function", inputs={}, params={})


def test_allowlisted_function_accepted(adapter):
    """
    T007: Test that allowlisted functions like subplots and savefig are accepted by the safety layer.
    """
    # We don't necessarily need to fully execute them, just verify they pass the safety check.
    # We'll mock the actual pyplot calls to avoid side effects.
    with patch("matplotlib.pyplot.subplots") as mock_subplots:
        mock_subplots.return_value = (MagicMock(), MagicMock())

        # This call should not be blocked by the safety layer.
        # Even if it fails later due to missing logic, it shouldn't raise "not allowed".
        try:
            adapter.execute("base.matplotlib.pyplot.subplots", inputs={}, params={})
        except ValueError as e:
            if any(
                word in str(e).lower() for word in ["blocked", "denied", "not allowed", "unknown"]
            ):
                pytest.fail(f"Safety layer incorrectly blocked allowlisted function: {e}")
            # Other errors are fine for now as we are testing the adapter wrapper
        except Exception:
            # Other exceptions are also fine, as long as it's not a safety rejection
            pass


def test_discovery_metadata(adapter):
    """
    Test that discovery returns correct IO patterns and parameters.
    """
    from bioimage_mcp.registry.dynamic.models import IOPattern

    module_config = {"modules": ["matplotlib.pyplot", "matplotlib.figure", "matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    # Check subplots
    subplots = next(fn for fn in discovered if fn.name == "subplots")
    assert subplots.io_pattern == IOPattern.CONSTRUCTOR
    assert "nrows" in subplots.parameters
    assert subplots.parameters["nrows"].type == "integer"
    assert subplots.parameters["nrows"].default == 1

    # Check savefig
    savefig = next(fn for fn in discovered if fn.name == "savefig")
    assert savefig.io_pattern == IOPattern.OBJECT_TO_IMAGE
    assert "format" in savefig.parameters

    # Check imshow
    imshow = next(fn for fn in discovered if fn.name == "imshow")
    assert imshow.io_pattern == IOPattern.OBJECTREF_CHAIN
    assert "cmap" in imshow.parameters

    # Check patches
    module_config_patches = {"modules": ["matplotlib.patches"]}
    discovered_patches = adapter.discover(module_config_patches)
    circle = next(fn for fn in discovered_patches if fn.name == "Circle")
    assert circle.io_pattern == IOPattern.CONSTRUCTOR
    assert "radius" in circle.parameters
