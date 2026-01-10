from bioimage_mcp.registry.dynamic.xarray_allowlists import (
    XARRAY_DATAARRAY_ALLOWLIST,
    XARRAY_DATAARRAY_CLASS,
    XARRAY_DENYLIST,
    XARRAY_TOPLEVEL_ALLOWLIST,
    XARRAY_UFUNC_ALLOWLIST,
    SignatureType,
    XarrayFunctionType,
    is_allowed_method,
)


def test_enums():
    assert XarrayFunctionType.TOPLEVEL.value == "toplevel"
    assert XarrayFunctionType.UFUNC.value == "ufunc"
    assert XarrayFunctionType.DATAARRAY_CLASS.value == "class"
    assert XarrayFunctionType.DATAARRAY_METHOD.value == "method"
    assert XarrayFunctionType.ACCESSOR.value == "accessor"

    assert SignatureType.SINGLE_INPUT.value == "single"
    assert SignatureType.MULTI_INPUT.value == "multi"
    assert SignatureType.BINARY.value == "binary"
    assert SignatureType.CONSTRUCTOR.value == "constructor"
    assert SignatureType.INSTANCE_METHOD.value == "instance"
    assert SignatureType.SPECIAL.value == "special"


def test_dataarray_class():
    assert len(XARRAY_DATAARRAY_CLASS) == 1
    assert "DataArray" in XARRAY_DATAARRAY_CLASS
    assert XARRAY_DATAARRAY_CLASS["DataArray"]["signature_type"] == SignatureType.CONSTRUCTOR


def test_toplevel_allowlist():
    assert len(XARRAY_TOPLEVEL_ALLOWLIST) == 15
    assert "concat" in XARRAY_TOPLEVEL_ALLOWLIST
    assert "merge" in XARRAY_TOPLEVEL_ALLOWLIST


def test_ufunc_allowlist():
    assert len(XARRAY_UFUNC_ALLOWLIST) == 60
    assert "add" in XARRAY_UFUNC_ALLOWLIST
    assert "sqrt" in XARRAY_UFUNC_ALLOWLIST


def test_dataarray_method_allowlist():
    assert len(XARRAY_DATAARRAY_ALLOWLIST) == 64
    assert "mean" in XARRAY_DATAARRAY_ALLOWLIST
    assert "isel" in XARRAY_DATAARRAY_ALLOWLIST
    assert "to_bioimage" in XARRAY_DATAARRAY_ALLOWLIST


def test_denylist():
    assert isinstance(XARRAY_DENYLIST, frozenset)
    assert "values" in XARRAY_DENYLIST
    assert "load" in XARRAY_DENYLIST
    assert "compute" in XARRAY_DENYLIST


def test_is_allowed_method():
    # Test allowed methods (from XARRAY_DATAARRAY_ALLOWLIST)
    assert is_allowed_method("mean") is True
    assert is_allowed_method("isel") is True
    assert is_allowed_method("to_bioimage") is True

    # Test denied methods
    assert is_allowed_method("values") is False
    assert is_allowed_method("load") is False

    # Test unknown method
    assert is_allowed_method("unknown_method") is False


def test_no_overlap():
    toplevel_keys = set(XARRAY_TOPLEVEL_ALLOWLIST.keys())
    ufunc_keys = set(XARRAY_UFUNC_ALLOWLIST.keys())
    method_keys = set(XARRAY_DATAARRAY_ALLOWLIST.keys())

    # Check overlap with denylist
    assert not (toplevel_keys & XARRAY_DENYLIST)
    assert not (ufunc_keys & XARRAY_DENYLIST)
    assert not (method_keys & XARRAY_DENYLIST)
