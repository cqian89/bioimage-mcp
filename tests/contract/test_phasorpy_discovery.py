"""Contract tests for PhasorPy dynamic discovery."""

import pytest
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern, FunctionMetadata


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

    # This is expected to FAIL until implementation (currently returns 2)
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
    """T017: Plot functions return PLOT IOPattern."""
    adapter = PhasorPyAdapter()
    module_config = {"modules": ["phasorpy.plot"]}
    discovered = adapter.discover(module_config)

    # Find functions that should be categorized as PLOT
    # This is expected to FAIL until implementation
    plot_fns = [fn for fn in discovered if "plot" in fn.name.lower()]
    assert len(plot_fns) > 0, "No plot functions discovered"

    for fn in plot_fns:
        assert fn.io_pattern == IOPattern.PLOT, f"Function {fn.name} should have PLOT pattern"
