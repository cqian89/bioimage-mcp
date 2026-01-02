"""
Unit tests for BaseAdapter protocol interface.

Tests that the BaseAdapter protocol exists and defines the correct interface
for library adapters in the dynamic registry system.
"""

import inspect
from typing import Protocol


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
        discover_attr = BaseAdapter.discover
        assert callable(discover_attr) or inspect.isfunction(discover_attr)

    def test_base_adapter_has_execute_method(self):
        """BaseAdapter protocol should define execute method."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check that execute method exists
        assert hasattr(BaseAdapter, "execute")

        # Verify it's a method (not just an attribute)
        execute_attr = BaseAdapter.execute
        assert callable(execute_attr) or inspect.isfunction(execute_attr)

    def test_base_adapter_has_resolve_io_pattern_method(self):
        """BaseAdapter protocol should define resolve_io_pattern method."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check that resolve_io_pattern method exists
        assert hasattr(BaseAdapter, "resolve_io_pattern")

        # Verify it's a method (not just an attribute)
        resolve_attr = BaseAdapter.resolve_io_pattern
        assert callable(resolve_attr) or inspect.isfunction(resolve_attr)

    def test_base_adapter_has_generate_dimension_hints_method(self):
        """BaseAdapter protocol should define generate_dimension_hints method."""
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter

        # Check that generate_dimension_hints method exists
        assert hasattr(BaseAdapter, "generate_dimension_hints")

        # Verify it's a method (not just an attribute)
        hints_attr = BaseAdapter.generate_dimension_hints
        assert callable(hints_attr) or inspect.isfunction(hints_attr)

    def test_concrete_class_satisfies_protocol(self):
        """A concrete class implementing all methods should satisfy BaseAdapter protocol."""
        from typing import Any

        from bioimage_mcp.artifacts.base import Artifact
        from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
        from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

        # Define a concrete implementation
        class DummyAdapter:
            """Dummy adapter for testing protocol conformance."""

            def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
                """Discover functions from module."""
                return []

            def execute(
                self, fn_id: str, inputs: list[Artifact], params: dict[str, Any]
            ) -> list[Artifact]:
                """Execute a function."""
                return []

            def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
                """Resolve I/O pattern from function signature."""
                return IOPattern.GENERIC

            def generate_dimension_hints(self, module_name: str, func_name: str) -> Any:
                """Generate dimension hints for agent guidance."""
                return None

        # Create an instance
        adapter = DummyAdapter()

        # Verify it satisfies the protocol
        # (In Python, structural subtyping means any class with the right methods works)
        assert isinstance(adapter, BaseAdapter)
