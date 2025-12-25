"""
Unit tests for BaseAdapter protocol interface.

Tests that the BaseAdapter protocol exists and defines the correct interface
for library adapters in the dynamic registry system.
"""

import inspect
from typing import get_type_hints, Protocol, runtime_checkable

import pytest


class TestBaseAdapterProtocol:
    """Test cases for BaseAdapter protocol interface."""

    def test_base_adapter_protocol_exists(self):
        """BaseAdapter protocol should be importable from registry.dynamic.adapters."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        assert BaseAdapter is not None
        assert inspect.isclass(BaseAdapter)

    def test_base_adapter_is_protocol(self):
        """BaseAdapter should be a typing.Protocol."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check if it's a Protocol subclass
        assert issubclass(BaseAdapter, Protocol)

    def test_base_adapter_has_discover_method(self):
        """BaseAdapter protocol should define discover method."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check that discover method exists
        assert hasattr(BaseAdapter, "discover")

        # Verify it's a method (not just an attribute)
        discover_attr = getattr(BaseAdapter, "discover")
        assert callable(discover_attr) or inspect.isfunction(discover_attr)

    def test_base_adapter_has_execute_method(self):
        """BaseAdapter protocol should define execute method."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check that execute method exists
        assert hasattr(BaseAdapter, "execute")

        # Verify it's a method (not just an attribute)
        execute_attr = getattr(BaseAdapter, "execute")
        assert callable(execute_attr) or inspect.isfunction(execute_attr)

    def test_base_adapter_has_resolve_io_pattern_method(self):
        """BaseAdapter protocol should define resolve_io_pattern method."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check that resolve_io_pattern method exists
        assert hasattr(BaseAdapter, "resolve_io_pattern")

        # Verify it's a method (not just an attribute)
        resolve_attr = getattr(BaseAdapter, "resolve_io_pattern")
        assert callable(resolve_attr) or inspect.isfunction(resolve_attr)

    def test_concrete_class_satisfies_protocol(self):
        """A concrete class implementing all methods should satisfy BaseAdapter protocol."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
        from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
        from bioimage_mcp.artifacts.base import Artifact
        from typing import List, Dict, Any

        # Define a concrete implementation
        class DummyAdapter:
            """Dummy adapter for testing protocol conformance."""

            def discover(self, module_config: Dict[str, Any]) -> List[FunctionMetadata]:
                """Discover functions from module."""
                return []

            def execute(
                self, fn_id: str, inputs: List[Artifact], params: Dict[str, Any]
            ) -> List[Artifact]:
                """Execute a function."""
                return []

            def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
                """Resolve I/O pattern from function signature."""
                return IOPattern.GENERIC

        # Create an instance
        adapter = DummyAdapter()

        # Verify it satisfies the protocol
        # (In Python, structural subtyping means any class with the right methods works)
        assert isinstance(adapter, BaseAdapter)
