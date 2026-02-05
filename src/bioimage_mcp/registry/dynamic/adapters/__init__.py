from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement


@runtime_checkable
class BaseAdapter(Protocol):
    """Protocol for library adapters in dynamic registry.

    All adapters must implement these three methods to enable
    discovery, execution, and I/O pattern resolution.
    """

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from a module configuration.

        Args:
            module_config: Configuration dictionary for the module to introspect.

        Returns:
            List of discovered function metadata.
        """
        ...

    def execute(self, fn_id: str, inputs: list[Artifact], params: dict[str, Any]) -> list[Artifact]:
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

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance.

        Args:
            module_name: Name of the module containing the function.
            func_name: Name of the function.

        Returns:
            DimensionRequirement or None if no specific requirements.
        """
        ...


# Global adapter registry - populated with default adapters
# This registry is shared across server and tool processes
ADAPTER_REGISTRY: dict[str, Any] = {}

# List of known adapter names for lazy loading verification
KNOWN_ADAPTERS = {
    "matplotlib",
    "phasorpy",
    "scipy",
    "skimage",
    "xarray",
    "pandas",
    "cellpose",
    "tttrlib",
    "microsam",
}


def populate_default_adapters() -> None:
    """Populate registry with default adapters if not already populated."""
    if ADAPTER_REGISTRY:
        return

    # Import adapters here to avoid circular imports
    from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter
    from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry
    from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
    from bioimage_mcp.registry.dynamic.adapters.scipy import ScipyAdapter
    from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter
    from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry

    ADAPTER_REGISTRY["matplotlib"] = MatplotlibAdapter()
    ADAPTER_REGISTRY["phasorpy"] = PhasorPyAdapter()
    ADAPTER_REGISTRY["scipy"] = ScipyAdapter()
    ADAPTER_REGISTRY["skimage"] = SkimageAdapter()
    ADAPTER_REGISTRY["xarray"] = XarrayAdapterForRegistry()
    ADAPTER_REGISTRY["pandas"] = PandasAdapterForRegistry()

    try:
        from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

        ADAPTER_REGISTRY["cellpose"] = CellposeAdapter()
    except ImportError:
        pass  # cellpose not installed, skip adapter

    # Import tttrlib adapter (manual schema adapter)
    try:
        from bioimage_mcp.registry.dynamic.adapters.tttrlib import TttrlibAdapter

        ADAPTER_REGISTRY["tttrlib"] = TttrlibAdapter()
    except ImportError:
        pass  # tttrlib not installed, skip adapter

    # Import microsam adapter
    try:
        from bioimage_mcp.registry.dynamic.adapters.microsam import MicrosamAdapter

        ADAPTER_REGISTRY["microsam"] = MicrosamAdapter()
    except ImportError:
        pass  # microsam dependencies (or module) not found, skip adapter


# No longer populate on module import to enable sub-second meta.list (T13)
# Clients should call populate_default_adapters() if they need the instances.


__all__ = ["BaseAdapter", "ADAPTER_REGISTRY", "KNOWN_ADAPTERS", "populate_default_adapters"]
