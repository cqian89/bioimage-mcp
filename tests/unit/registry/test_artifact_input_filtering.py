from __future__ import annotations

from unittest.mock import MagicMock
from pathlib import Path
from bioimage_mcp.registry.dynamic.models import IOPattern
from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry
from bioimage_mcp.registry.dynamic.adapters.scipy_spatial import ScipySpatialAdapter
from bioimage_mcp.registry.engine import DiscoveryEngine
from bioimage_mcp.registry.manifest_schema import ToolManifest


def test_xarray_concat_objs_not_in_params():
    """Verify objs is filtered from params for concat."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    concat_fn = next((f for f in discovered if f.name == "concat"), None)
    assert concat_fn is not None
    assert "objs" not in concat_fn.parameters
    assert concat_fn.io_pattern == IOPattern.MULTI_INPUT


def test_xarray_merge_objects_not_in_params():
    """Verify objects is filtered from params for merge."""
    adapter = XarrayAdapterForRegistry()
    discovered = adapter.discover({})

    merge_fn = next((f for f in discovered if f.name == "merge"), None)
    assert merge_fn is not None
    assert "objects" not in merge_fn.parameters


def test_scipy_cdist_xa_xb_not_in_params():
    """Verify XA and XB are filtered from params for cdist."""
    adapter = ScipySpatialAdapter()
    discovered = adapter.discover({"modules": ["scipy.spatial", "scipy.spatial.distance"]})

    cdist_fn = next((f for f in discovered if f.name == "cdist"), None)
    assert cdist_fn is not None
    assert "XA" not in cdist_fn.parameters
    assert "XB" not in cdist_fn.parameters
    # Verify manual params are preserved
    assert "metric" in cdist_fn.parameters


def test_engine_filters_artifact_input_names():
    """Verify engine hardcoded list filters artifact input params."""
    engine = DiscoveryEngine()

    # Create a mock ToolManifest
    manifest = MagicMock(spec=ToolManifest)
    manifest.tool_id = "test.tool"
    manifest.manifest_path = Path("test/manifest.yaml")

    # Create a mock callable from AST inspection
    mock_sc = MagicMock()
    mock_sc.name = "my_func"
    mock_sc.qualified_name = "module.my_func"
    mock_sc.docstring = "Test function"

    # Mock parameters that should be filtered
    p1 = MagicMock()
    p1.name = "objs"
    p1.annotation = "list"
    p1.default = None

    p2 = MagicMock()
    p2.name = "my_param"
    p2.annotation = "int"
    p2.default = 10

    mock_sc.parameters = [p1, p2]

    # Mock source and adapter
    source = MagicMock()
    source.prefix = "src"
    source.adapter = "generic"

    # Run _process_callable
    fn = engine._process_callable(manifest, mock_sc, source, None, {})

    assert fn is not None
    assert "objs" not in fn.params_schema["properties"]
    assert "my_param" in fn.params_schema["properties"]
    assert fn.params_schema["properties"]["my_param"]["type"] == "integer"
