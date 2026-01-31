from __future__ import annotations

from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter


def test_regionprops_table_schema_enrichment():
    """Test that regionprops_table schema is enriched with properties and x-property-groups."""
    adapter = SkimageAdapter()
    results = adapter.discover({"module_name": "skimage.measure", "include": ["regionprops_table"]})

    # Find regionprops_table metadata
    meta = next((m for m in results if m.name == "regionprops_table"), None)
    assert meta is not None

    # Check properties parameter
    props_param = meta.parameters.get("properties")
    assert props_param is not None
    assert props_param.items is not None

    # Check enum contents
    enum_values = props_param.items.get("enum", [])
    assert len(enum_values) > 40  # Should have ~44 properties now
    assert "intensity_mean" in enum_values
    assert "eccentricity" in enum_values
    assert "area" in enum_values

    # Check x-property-groups
    groups = props_param.items.get("x-property-groups")
    assert groups is not None
    assert "basic" in groups
    assert "intensity" in groups
    assert "2d_only" in groups

    # Check basic group
    assert "area" in groups["basic"]["values"]
    assert "centroid" in groups["basic"]["values"]

    # Check intensity group
    assert groups["intensity"]["requires_input"] == "intensity_image"
    assert "intensity_mean" in groups["intensity"]["values"]
    assert "intensity_max" in groups["intensity"]["values"]

    # Check 2d_only group
    assert groups["2d_only"]["constraint"] == "label_image.ndim == 2"
    assert "eccentricity" in groups["2d_only"]["values"]
    assert "orientation" in groups["2d_only"]["values"]

    # Check description
    assert "Properties to compute" in props_param.description
    assert "x-property-groups" in props_param.description
    assert str(len(enum_values)) in props_param.description


def test_regionprops_redirect_schema_enrichment():
    """Test that regionprops (redirected to regionprops_table) also gets enriched schema."""
    adapter = SkimageAdapter()
    results = adapter.discover({"module_name": "skimage.measure", "include": ["regionprops"]})

    meta = next((m for m in results if m.name == "regionprops"), None)
    assert meta is not None

    props_param = meta.parameters.get("properties")
    assert props_param is not None
    assert props_param.items is not None
    assert "intensity_mean" in props_param.items.get("enum", [])
    assert "x-property-groups" in props_param.items
