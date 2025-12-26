"""
Adapter protocol for dynamic function registry.

Defines the base protocol that all library adapters must implement
to integrate with the dynamic registry system.
"""

from typing import Any, Dict, List, Protocol, runtime_checkable

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


@runtime_checkable
class BaseAdapter(Protocol):
    """Protocol for library adapters in dynamic registry.

    All adapters must implement these three methods to enable
    discovery, execution, and I/O pattern resolution.
    """

    def discover(self, module_config: Dict[str, Any]) -> List[FunctionMetadata]:
        """Discover functions from a module configuration.

        Args:
            module_config: Configuration dictionary for the module to introspect.

        Returns:
            List of discovered function metadata.
        """
        ...

    def execute(self, fn_id: str, inputs: List[Artifact], params: Dict[str, Any]) -> List[Artifact]:
        """Execute a discovered function.

        Args:
            fn_id: Unique function identifier.
            inputs: List of input artifacts.
            params: Parameter dictionary.

        Returns:
            List of output artifacts.
        """
        ...

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern from function signature.

        Args:
            func_name: Name of the function.
            signature: Function signature object.

        Returns:
            Categorized I/O pattern.
        """
        ...


# Global adapter registry - populated with default adapters
# This registry is shared across server and tool processes
ADAPTER_REGISTRY: Dict[str, Any] = {}


def _populate_default_adapters() -> None:
    """Populate registry with default adapters if not already populated."""
    if ADAPTER_REGISTRY:
        return

    # Import adapters here to avoid circular imports
    from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
    from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
    from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter

    ADAPTER_REGISTRY["phasorpy"] = PhasorPyAdapter()
    ADAPTER_REGISTRY["scipy"] = ScipyNdimageAdapter()
    ADAPTER_REGISTRY["skimage"] = SkimageAdapter()


# Populate on module import
_populate_default_adapters()


__all__ = ["BaseAdapter", "ADAPTER_REGISTRY"]
