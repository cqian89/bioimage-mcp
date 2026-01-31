from __future__ import annotations

import logging

from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry

logger = logging.getLogger(__name__)


def test_dataarray_reduction_methods_have_dim_param():
    """Reduction methods like mean, sum should have 'dim' parameter from introspection."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    # Find mean method
    mean_meta = next((m for m in discovered if m.fn_id == "base.xarray.DataArray.mean"), None)
    assert mean_meta is not None, "mean method should be discovered"
    assert "dim" in mean_meta.parameters, "mean should have 'dim' parameter"
    assert mean_meta.parameters["dim"].required is False, "dim should be optional"


def test_reduction_methods_have_common_params():
    """Verify multiple reduction methods (mean, sum, std) have common parameters."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    methods = ["mean", "sum", "std"]
    for method_name in methods:
        fn_id = f"base.xarray.DataArray.{method_name}"
        meta = next((m for m in discovered if m.fn_id == fn_id), None)
        assert meta is not None, f"{method_name} method should be discovered"
        assert "dim" in meta.parameters, f"{method_name} should have 'dim' parameter"
        assert meta.parameters["dim"].required is False


def test_toplevel_concat_has_dim_param():
    """Top-level concat function should have 'dim' parameter."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    concat_meta = next((m for m in discovered if m.fn_id == "base.xarray.concat"), None)
    assert concat_meta is not None, "concat function should be discovered"
    assert "dim" in concat_meta.parameters, "concat should have 'dim' parameter"


def test_allowlist_params_override_introspected():
    """Explicit allowlist params should override introspected ones."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    # transpose has explicit 'dims' in allowlist with required=True
    transpose_meta = next(
        (m for m in discovered if m.fn_id == "base.xarray.DataArray.transpose"), None
    )
    assert transpose_meta is not None, "transpose method should be discovered"
    assert "dims" in transpose_meta.parameters, "transpose should have 'dims' parameter"

    # Verify it matches allowlist: "required": True, type: "array"
    assert transpose_meta.parameters["dims"].required is True
    assert transpose_meta.parameters["dims"].type == "array"
    assert transpose_meta.parameters["dims"].description == "New order of dimensions"


def test_ufunc_introspection():
    """Verify ufuncs are discovered and have parameters."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    # base.xarray.ufuncs.add
    add_meta = next((m for m in discovered if m.fn_id == "base.xarray.ufuncs.add"), None)
    assert add_meta is not None, "add ufunc should be discovered"

    # numpy.add has 'where' parameter which should be introspected
    assert "where" in add_meta.parameters
    assert add_meta.parameters["where"].required is False
