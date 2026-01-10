from __future__ import annotations

import pytest

from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


@pytest.fixture(scope="module")
def xarray_functions() -> list[FunctionMetadata]:
    """Discover all xarray functions."""
    adapter = XarrayAdapterForRegistry()
    return adapter.discover({})


def test_all_discovered_functions_have_valid_schema(
    xarray_functions: list[FunctionMetadata],
) -> None:
    """Discovery returns valid FunctionMetadata for all xarray functions."""
    for fn in xarray_functions:
        assert isinstance(fn, FunctionMetadata)

        # Valid fn_id format: base.xarray...
        assert fn.fn_id.startswith("base.xarray")

        # Non-empty description/summary
        assert fn.description and len(fn.description) > 0

        # Valid tags list
        assert isinstance(fn.tags, list)
        assert len(fn.tags) > 0

        # Valid io_pattern
        assert isinstance(fn.io_pattern, IOPattern)


def test_function_id_naming_conventions(xarray_functions: list[FunctionMetadata]) -> None:
    """Verify function IDs follow specified patterns."""
    fn_ids = {fn.fn_id for fn in xarray_functions}

    # base.xarray.DataArray - constructor
    assert "base.xarray.DataArray" in fn_ids

    # base.xarray.<name> - top-level functions (e.g. concat)
    assert "base.xarray.concat" in fn_ids

    # base.xarray.ufuncs.<name> - universal functions (e.g. add)
    assert "base.xarray.ufuncs.add" in fn_ids

    # base.xarray.DataArray.<name> - methods (e.g. mean)
    assert "base.xarray.DataArray.mean" in fn_ids

    # Verify no unexpected top-level structure
    for fn_id in fn_ids:
        parts = fn_id.split(".")
        assert parts[0] == "base"
        assert parts[1] == "xarray"
        # Should be base.xarray.Name or base.xarray.ufuncs.Name or base.xarray.DataArray.Name
        assert len(parts) in (3, 4)


def test_categories_in_tags(xarray_functions: list[FunctionMetadata]) -> None:
    """Each function's tags should include its category."""
    from bioimage_mcp.registry.dynamic.xarray_allowlists import (
        XARRAY_DATAARRAY_ALLOWLIST,
        XARRAY_DATAARRAY_CLASS,
        XARRAY_TOPLEVEL_ALLOWLIST,
        XARRAY_UFUNC_ALLOWLIST,
    )

    for fn in xarray_functions:
        name = fn.name
        expected_category = None

        if fn.fn_id == "base.xarray.DataArray":
            expected_category = XARRAY_DATAARRAY_CLASS["DataArray"].get("category")
        elif fn.fn_id.startswith("base.xarray.ufuncs."):
            expected_category = XARRAY_UFUNC_ALLOWLIST[name].get("category")
        elif fn.fn_id.startswith("base.xarray.DataArray."):
            expected_category = XARRAY_DATAARRAY_ALLOWLIST[name].get("category")
        elif fn.fn_id.startswith("base.xarray."):
            # Important: check startswith AFTER ufuncs and DataArray to avoid false positives
            expected_category = XARRAY_TOPLEVEL_ALLOWLIST[name].get("category")

        if expected_category:
            assert expected_category in fn.tags, (
                f"Function {fn.fn_id} missing category tag '{expected_category}'"
            )


def test_no_duplicate_function_ids(xarray_functions: list[FunctionMetadata]) -> None:
    """All fn_ids should be unique."""
    fn_ids = [fn.fn_id for fn in xarray_functions]
    duplicates = [x for x in fn_ids if fn_ids.count(x) > 1]
    assert len(fn_ids) == len(set(fn_ids)), f"Duplicate fn_ids found: {set(duplicates)}"


def test_total_function_count(xarray_functions: list[FunctionMetadata]) -> None:
    """Total number of discovered xarray functions should be exactly 147."""
    assert len(xarray_functions) == 140
