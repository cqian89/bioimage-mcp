from __future__ import annotations

import inspect
import pytest
from pydantic import ValidationError


def test_dynamic_source_extension():
    """T006: Test DynamicSource extension with target_class and class_methods."""
    from bioimage_mcp.registry.manifest_schema import DynamicSource

    # Test valid extension
    ds = DynamicSource(
        adapter="python",
        prefix="cellpose",
        modules=["cellpose.models"],
        target_class="cellpose.models.CellposeModel",
        class_methods=["eval", "train"],
    )

    assert ds.target_class == "cellpose.models.CellposeModel"
    assert ds.class_methods == ["eval", "train"]


def test_kwargs_filtering_in_discovery():
    """T047: Test that methods with **kwargs are excluded during discovery.

    Requirement: Creates a mock class with a method that has **kwargs,
    invokes discovery mechanism, asserts that the method with **kwargs
    is NOT returned in discovery results.
    """
    from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter
    import types
    import sys
    import inspect

    # Create a dummy module
    mod_name = "test_discovery_module"
    module = types.ModuleType(mod_name)
    sys.modules[mod_name] = module

    try:

        def good_func(image, sigma: float = 1.0):
            """Good function."""
            return image

        def bad_func(image, **kwargs):
            """Bad function with kwargs."""
            return image

        module.good_func = good_func
        module.bad_func = bad_func

        # Verify they are in the module
        assert "good_func" in dir(module)
        assert "bad_func" in dir(module)

        # Verify bad_func has **kwargs
        sig = inspect.signature(bad_func)
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

        adapter = SkimageAdapter()
        # Mock module_config as it would come from a DynamicSource
        module_config = {"modules": [mod_name], "include": ["*"]}

        # Invoke discovery mechanism
        results = adapter.discover(module_config)

        # Verify results
        func_names = [r.name for r in results]

        # good_func should be discovered
        assert "good_func" in func_names

        # bad_func should NOT be discovered (T047 requirement)
        assert "bad_func" not in func_names, (
            "Discovery should exclude methods with **kwargs unless overlay exists"
        )

    finally:
        if mod_name in sys.modules:
            del sys.modules[mod_name]


def test_dynamic_source_validation():
    """T006: Test validation of DynamicSource fields."""
    from bioimage_mcp.registry.manifest_schema import DynamicSource

    # modules is still required
    with pytest.raises(ValidationError):
        DynamicSource(adapter="python", prefix="test", target_class="MyClass")
