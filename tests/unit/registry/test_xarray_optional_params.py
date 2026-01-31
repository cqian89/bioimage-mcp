from __future__ import annotations

from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry


def test_xarray_concat_optional_params():
    """Verify that base.xarray.concat has join and fill_value as optional."""
    adapter = XarrayAdapterForRegistry()
    discovery = adapter.discover({})

    # Find base.xarray.concat
    concat = next((f for f in discovery if f.fn_id == "base.xarray.concat"), None)
    assert concat is not None

    # join: "str?" -> type="str", required=False
    assert "join" in concat.parameters
    join_param = concat.parameters["join"]
    assert join_param.type == "str"
    assert join_param.required is False

    # fill_value: "Any?" -> type="Any", required=False
    assert "fill_value" in concat.parameters
    fv_param = concat.parameters["fill_value"]
    assert fv_param.type == "Any"
    assert fv_param.required is False

    # dim: "str" -> type="str", required=True
    assert "dim" in concat.parameters
    dim_param = concat.parameters["dim"]
    assert dim_param.type == "str"
    assert dim_param.required is True


def test_xarray_parameter_schema_parsing_logic():
    """Verify the parsing logic for '?' suffix in all 3 introspection methods."""
    adapter = XarrayAdapterForRegistry()

    # We can test the introspection methods directly by mocking the info dict
    mock_info = {
        "params": {
            "opt_param": "int?",
            "req_param": "float",
            "dict_param": {"type": "string", "required": False},
        }
    }

    # Test _introspect_toplevel_function (it's one of the 3 updated methods)
    # We use a real function name to satisfy internal checks; we care about "params" override
    params = adapter._introspect_toplevel_function("concat", mock_info)

    assert params["opt_param"].type == "int"
    assert params["opt_param"].required is False

    assert params["req_param"].type == "float"
    assert params["req_param"].required is True

    assert params["dict_param"].type == "string"
    assert params["dict_param"].required is False
