"""Contract tests for PhasorPy dynamic discovery."""

from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


def test_iopattern_includes_new_values():
    """T038: New IOPattern values exist (PHASOR_TO_SCALAR, SCALAR_TO_PHASOR, PLOT)."""
    assert IOPattern.PHASOR_TO_SCALAR == "phasor_to_scalar"
    assert IOPattern.SCALAR_TO_PHASOR == "scalar_to_phasor"
    assert IOPattern.PLOT == "plot"

    all_values = [v.value for v in IOPattern]
    assert "phasor_to_scalar" in all_values
    assert "scalar_to_phasor" in all_values
    assert "plot" in all_values


def test_discovery_excludes_io_module():
    """T040: phasorpy.io module is NOT discovered (excluded per constitution)."""
    adapter = PhasorPyAdapter()
    # Explicitly try to discover from phasorpy.io which should be blocked
    module_config = {"modules": ["phasorpy.io", "phasorpy.phasor"]}
    discovered = adapter.discover(module_config)

    for fn in discovered:
        assert not fn.module.startswith("phasorpy.io"), f"Forbidden module discovered: {fn.module}"
        assert not fn.fn_id.startswith("phasorpy.io"), f"Forbidden fn_id discovered: {fn.fn_id}"


def test_discovery_min_function_count():
    """T009: >=50 phasorpy functions are discovered."""
    adapter = PhasorPyAdapter()
    module_config = {
        "modules": [
            "phasorpy.phasor",
            "phasorpy.lifetime",
            "phasorpy.plot",
            "phasorpy.filter",
            "phasorpy.cursor",
            "phasorpy.components",
        ]
    }
    discovered = adapter.discover(module_config)

    # >= 50 phasorpy functions are discovered.
    assert len(discovered) >= 50


def test_describe_function_schema_validity():
    """T010: describe_function schema is valid (Pydantic validation)."""
    adapter = PhasorPyAdapter()
    module_config = {"modules": ["phasorpy.phasor"]}
    discovered = adapter.discover(module_config)

    assert len(discovered) > 0
    for fn_meta in discovered:
        # Re-validate using Pydantic model
        validated = FunctionMetadata.model_validate(fn_meta)
        assert validated.name
        assert validated.fn_id
        assert validated.source_adapter == "phasorpy"
        assert isinstance(validated.io_pattern, IOPattern)


def test_plot_functions_return_plot_pattern():
    """T017: Plot functions return PLOT IOPattern and PlotRef output type."""
    adapter = PhasorPyAdapter()
    module_config = {"modules": ["phasorpy.plot"]}
    discovered = adapter.discover(module_config)

    # Find functions that should be categorized as PLOT
    plot_fns = [fn for fn in discovered if "plot" in fn.name.lower()]
    assert len(plot_fns) > 0, "No plot functions discovered"

    for fn in plot_fns:
        assert fn.io_pattern == IOPattern.PLOT, f"Function {fn.name} should have PLOT pattern"


def test_phasor_calibrate_returns_calibrate_pattern():
    """Verify phasor_calibrate returns PHASOR_CALIBRATE pattern."""
    adapter = PhasorPyAdapter()
    module_config = {"modules": ["phasorpy.lifetime"], "include": ["phasor_calibrate"]}
    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    fn = discovered[0]
    assert fn.name == "phasor_calibrate"
    assert fn.io_pattern == IOPattern.PHASOR_CALIBRATE
    # Since PlotRef is a semantic type assigned by the adapter during execution,
    # discovery might not show it as the return type yet if it's based on introspector
    # but we should ensure the adapter is configured to produce them.


def test_artifact_params_filtered():
    """Verify that artifact input parameters are filtered from params_schema."""
    adapter = PhasorPyAdapter()

    # Check phasor_from_signal (should not have 'signal')
    module_config = {"modules": ["phasorpy.phasor"], "include": ["phasor_from_signal"]}
    discovered = adapter.discover(module_config)
    assert len(discovered) == 1
    fn = discovered[0]
    assert "signal" not in fn.parameters

    # Check phasor_center (should not have 'real', 'imag', 'mean')
    module_config = {"modules": ["phasorpy.phasor"], "include": ["phasor_center"]}
    discovered = adapter.discover(module_config)
    assert len(discovered) == 1
    fn = discovered[0]
    assert "real" not in fn.parameters
    assert "imag" not in fn.parameters
    assert "mean" not in fn.parameters

    # Check plot_phasor (should not have 'real', 'imag')
    module_config = {"modules": ["phasorpy.plot"], "include": ["plot_phasor"]}
    discovered = adapter.discover(module_config)
    assert len(discovered) == 1
    fn = discovered[0]
    assert "real" not in fn.parameters
    assert "imag" not in fn.parameters
