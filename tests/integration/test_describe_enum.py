from __future__ import annotations

import pytest


@pytest.mark.requires_base
@pytest.mark.integration
def test_regionprops_table_describe_has_enum(mcp_test_client):
    """Verify that describe for regionprops_table returns the enum for properties."""
    fn_id = "base.skimage.measure.regionprops_table"

    # Call describe through the MCP client
    # This should trigger introspection via meta.describe in the base env
    result = mcp_test_client.describe_function(id=fn_id)

    if "error" in result:
        pytest.fail(f"Describe failed: {result['error']}")

    assert "params_schema" in result, f"Result missing params_schema: {result}"
    params_schema = result["params_schema"]

    # 2. Verify that params_schema["properties"]["properties"] contains type: "array"
    assert "properties" in params_schema["properties"], (
        f"Missing 'properties' param in {params_schema['properties'].keys()}"
    )
    props_field = params_schema["properties"]["properties"]
    assert props_field["type"] == "array"

    # 3. Verify that params_schema["properties"]["properties"]["items"] exists
    # and contains an enum with valid property names like "area", "label", etc.
    assert "items" in props_field, f"Missing 'items' in {props_field}"
    items = props_field["items"]
    assert "enum" in items, f"Missing 'enum' in {items}"

    enum_values = items["enum"]
    assert "area" in enum_values
    assert "label" in enum_values
    assert "centroid" in enum_values
    assert "bbox" in enum_values

    # Should have many properties (typically 30+)
    assert len(enum_values) >= 20


@pytest.mark.requires_base
@pytest.mark.integration
def test_threshold_local_describe_has_enum(mcp_test_client):
    """Verify that describe for threshold_local returns the enum for method."""
    fn_id = "base.skimage.filters.threshold_local"

    result = mcp_test_client.describe_function(id=fn_id)

    if "error" in result:
        pytest.fail(f"Describe failed: {result['error']}")

    assert "params_schema" in result
    params_schema = result["params_schema"]

    assert "method" in params_schema["properties"]
    method_field = params_schema["properties"]["method"]

    assert "enum" in method_field
    assert set(method_field["enum"]) == {"generic", "gaussian", "mean", "median"}
