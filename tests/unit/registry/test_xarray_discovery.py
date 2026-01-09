from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry
from bioimage_mcp.registry.dynamic.models import FunctionMetadata


def test_xarray_discovery_returns_metadata():
    adapter = XarrayAdapterForRegistry()
    discovery = adapter.discover({})

    assert isinstance(discovery, list)
    assert len(discovery) == 147
    assert all(isinstance(fn, FunctionMetadata) for fn in discovery)


def test_xarray_discovery_prefixes():
    adapter = XarrayAdapterForRegistry()
    discovery = adapter.discover({})

    fn_ids = {fn.fn_id for fn in discovery}

    # Check constructor
    assert "base.xarray.DataArray" in fn_ids

    # Check top-level
    assert "base.xarray.concat" in fn_ids
    assert "base.xarray.where" in fn_ids

    # Check ufuncs
    assert "base.xarray.ufuncs.add" in fn_ids
    assert "base.xarray.ufuncs.sin" in fn_ids

    # Check methods
    assert "base.xarray.DataArray.mean" in fn_ids
    assert "base.xarray.DataArray.squeeze" in fn_ids


def test_xarray_discovery_fields():
    adapter = XarrayAdapterForRegistry()
    discovery = adapter.discover({})

    # Find one from each category to check fields
    concat = next(fn for fn in discovery if fn.fn_id == "base.xarray.concat")
    assert concat.name == "concat"
    assert concat.module == "xarray"
    assert concat.source_adapter == "xarray"
    assert "Concatenate arrays" in concat.description
    assert "combine" in concat.tags
    assert "xarray" in concat.tags

    add = next(fn for fn in discovery if fn.fn_id == "base.xarray.ufuncs.add")
    assert add.name == "add"
    assert add.module == "xarray"
    assert add.qualified_name == "xarray.add"
    assert "arithmetic" in add.tags

    mean = next(fn for fn in discovery if fn.fn_id == "base.xarray.DataArray.mean")
    assert mean.name == "mean"
    assert mean.module == "xarray.DataArray"
    assert mean.qualified_name == "xarray.DataArray.mean"
    assert "reduction" in mean.tags

    da_class = next(fn for fn in discovery if fn.fn_id == "base.xarray.DataArray")
    assert da_class.name == "DataArray"
    assert da_class.module == "xarray"
    assert da_class.qualified_name == "xarray.DataArray"
    assert "constructor" in da_class.tags
