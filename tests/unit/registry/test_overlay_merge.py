import pytest
from bioimage_mcp.registry.manifest_schema import Function, FunctionOverlay
from bioimage_mcp.registry.loader import merge_function_overlay


def test_function_overlay_instantiation():
    """Test that FunctionOverlay can be instantiated with various fields."""
    overlay = FunctionOverlay(
        fn_id="base.skimage.filters.gaussian",
        description="Enhanced Gaussian Blur",
        tags=["blur", "denoise"],
        params_override={
            "sigma": {"description": "Standard deviation for Gaussian kernel", "default": 1.0}
        },
    )
    assert overlay.fn_id == "base.skimage.filters.gaussian"
    assert overlay.description == "Enhanced Gaussian Blur"


def test_merge_function_overlay_simple():
    """Test merging an overlay into a discovered function."""
    discovered = Function(
        fn_id="base.skimage.filters.gaussian",
        tool_id="tools.base",
        name="gaussian",
        description="Original description",
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )
    overlay = FunctionOverlay(
        fn_id="base.skimage.filters.gaussian", description="Enhanced description", tags=["new-tag"]
    )

    merged = merge_function_overlay(discovered, overlay)

    assert merged.description == "Enhanced description"
    assert "new-tag" in merged.tags
    assert merged.name == "gaussian"  # Name should be preserved


def test_merge_function_overlay_params():
    """Test that params_override correctly updates params_schema."""
    discovered = Function(
        fn_id="base.skimage.filters.gaussian",
        tool_id="tools.base",
        name="gaussian",
        description="Original",
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )
    overlay = FunctionOverlay(
        fn_id="base.skimage.filters.gaussian",
        params_override={"sigma": {"description": "Updated sigma description"}},
    )

    merged = merge_function_overlay(discovered, overlay)

    assert merged.params_schema["properties"]["sigma"]["description"] == "Updated sigma description"
    assert merged.params_schema["properties"]["sigma"]["type"] == "number"  # Preserved
