"""Contract tests for Matplotlib dynamic discovery."""

import pytest
from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY


def test_matplotlib_adapter_registered():
    """T006: Assert 'matplotlib' key exists in ADAPTER_REGISTRY."""
    assert "matplotlib" in ADAPTER_REGISTRY, "Matplotlib adapter not found in ADAPTER_REGISTRY"


def test_matplotlib_functions_discoverable():
    """T006: Assert adapter.discover() returns functions with 'base.matplotlib.*' prefix."""
    try:
        from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
    except ImportError:
        pytest.fail("MatplotlibAdapter not yet implemented or not importable")

    adapter = MatplotlibAdapter()
    # Config for matplotlib discovery
    module_config = {"modules": ["matplotlib.pyplot", "matplotlib.figure", "matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    assert len(discovered) > 0, "No functions discovered by MatplotlibAdapter"
    for fn in discovered:
        assert fn.fn_id.startswith("base.matplotlib."), f"Unexpected fn_id: {fn.fn_id}"


def test_core_pyplot_functions_exposed():
    """T006: Assert key functions like base.matplotlib.pyplot.subplots, base.matplotlib.pyplot.figure are in discovered functions."""
    try:
        from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
    except ImportError:
        pytest.fail("MatplotlibAdapter not yet implemented")

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.pyplot"]}
    discovered = adapter.discover(module_config)

    fn_ids = {fn.fn_id for fn in discovered}
    assert "base.matplotlib.pyplot.subplots" in fn_ids
    assert "base.matplotlib.pyplot.figure" in fn_ids


def test_axes_methods_exposed():
    """T006: Assert base.matplotlib.Axes.imshow, base.matplotlib.Axes.plot, etc. are discoverable."""
    try:
        from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
    except ImportError:
        pytest.fail("MatplotlibAdapter not yet implemented")

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    fn_ids = {fn.fn_id for fn in discovered}
    assert "base.matplotlib.Axes.imshow" in fn_ids
    assert "base.matplotlib.Axes.plot" in fn_ids
    assert "base.matplotlib.Axes.scatter" in fn_ids
    assert "base.matplotlib.Axes.hist" in fn_ids
    assert "base.matplotlib.Axes.boxplot" in fn_ids
    assert "base.matplotlib.Axes.violinplot" in fn_ids


def test_figure_methods_exposed():
    """T006: Assert base.matplotlib.Figure.savefig is discoverable."""
    try:
        from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
    except ImportError:
        pytest.fail("MatplotlibAdapter not yet implemented")

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.figure"]}
    discovered = adapter.discover(module_config)

    fn_ids = {fn.fn_id for fn in discovered}
    assert "base.matplotlib.Figure.savefig" in fn_ids


def test_hist_schema():
    """T010: Verify base.matplotlib.Axes.hist schema."""
    try:
        from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
    except ImportError:
        pytest.fail("MatplotlibAdapter not yet implemented")

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    hist_fn = next((fn for fn in discovered if fn.fn_id == "base.matplotlib.Axes.hist"), None)
    assert hist_fn is not None, "base.matplotlib.Axes.hist not found in discovery"

    params = hist_fn.parameters
    assert "x" in params
    assert "bins" in params
    assert "range" in params
    assert "color" in params
    assert "alpha" in params

    # Verify some types if they match expectations
    assert params["bins"].type == "integer"
    assert params["alpha"].type == "number"


def test_imshow_schema():
    """T014: Verify base.matplotlib.Axes.imshow schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    imshow_fn = next((fn for fn in discovered if fn.fn_id == "base.matplotlib.Axes.imshow"), None)
    assert imshow_fn is not None, "base.matplotlib.Axes.imshow not found"

    params = imshow_fn.parameters
    assert "cmap" in params
    assert "origin" in params
    assert "alpha" in params
    assert "vmin" in params
    assert "vmax" in params


def test_add_patch_schema():
    """T014: Verify base.matplotlib.Axes.add_patch schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    add_patch_fn = next(
        (fn for fn in discovered if fn.fn_id == "base.matplotlib.Axes.add_patch"), None
    )
    assert add_patch_fn is not None, "base.matplotlib.Axes.add_patch not found"


def test_patches_schema():
    """T014: Verify base.matplotlib.patches schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.patches"]}
    discovered = adapter.discover(module_config)

    circle_fn = next(
        (fn for fn in discovered if fn.fn_id == "base.matplotlib.patches.Circle"), None
    )
    assert circle_fn is not None, "base.matplotlib.patches.Circle not found"
    assert "radius" in circle_fn.parameters
    assert "xy" in circle_fn.parameters

    rect_fn = next(
        (fn for fn in discovered if fn.fn_id == "base.matplotlib.patches.Rectangle"), None
    )
    assert rect_fn is not None, "base.matplotlib.patches.Rectangle not found"
    assert "width" in rect_fn.parameters
    assert "height" in rect_fn.parameters
    assert "xy" in rect_fn.parameters


def test_scatter_schema():
    """T022: Verify base.matplotlib.Axes.scatter schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    scatter_fn = next((fn for fn in discovered if fn.fn_id == "base.matplotlib.Axes.scatter"), None)
    assert scatter_fn is not None, "base.matplotlib.Axes.scatter not found"

    params = scatter_fn.parameters
    assert "x" in params
    assert "y" in params
    assert "s" in params
    assert "c" in params
    assert "marker" in params
    assert "cmap" in params
    assert "alpha" in params


def test_subplots_schema():
    """T018: Verify base.matplotlib.subplots schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.pyplot"]}
    discovered = adapter.discover(module_config)

    subplots_fn = next(
        (fn for fn in discovered if fn.fn_id == "base.matplotlib.pyplot.subplots"), None
    )
    assert subplots_fn is not None, "base.matplotlib.pyplot.subplots not found"

    params = subplots_fn.parameters
    assert "nrows" in params
    assert "ncols" in params
    assert "sharex" in params
    assert "sharey" in params
    assert "figsize" in params

    assert params["nrows"].type == "integer"
    assert params["ncols"].type == "integer"
    assert params["figsize"].type == "array"


def test_savefig_schema():
    """T030: Verify base.matplotlib.Figure.savefig schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.figure"]}
    discovered = adapter.discover(module_config)

    savefig_fn = next(
        (fn for fn in discovered if fn.fn_id == "base.matplotlib.Figure.savefig"), None
    )
    assert savefig_fn is not None, "base.matplotlib.Figure.savefig not found"

    params = savefig_fn.parameters
    assert "format" in params
    assert "dpi" in params
    assert "bbox_inches" in params
    assert "transparent" in params

    assert params["format"].type == "string"
    assert params["dpi"].type == "number"
    assert params["transparent"].type == "boolean"


def test_plot_schema():
    """T026: Verify base.matplotlib.Axes.plot schema."""
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

    adapter = MatplotlibAdapter()
    module_config = {"modules": ["matplotlib.axes"]}
    discovered = adapter.discover(module_config)

    plot_fn = next((fn for fn in discovered if fn.fn_id == "base.matplotlib.Axes.plot"), None)
    assert plot_fn is not None, "base.matplotlib.Axes.plot not found"

    params = plot_fn.parameters
    assert "x" in params
    assert "y" in params
    assert "fmt" in params
    assert "label" in params
    assert "linewidth" in params
    assert "color" in params
    assert "marker" in params
