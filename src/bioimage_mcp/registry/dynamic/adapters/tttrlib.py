"""
Tttrlib adapter for dynamic function registry.

This adapter handles tttrlib functions with manual schemas since
SWIG-wrapped C++ bindings don't support Python introspection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


class TttrlibAdapter:
    """Adapter for tttrlib library functions.

    Unlike other adapters, TttrlibAdapter uses manual schemas from the manifest
    because tttrlib is a SWIG-wrapped C++ library that doesn't expose Python signatures.
    """

    # Curated function list (matches manifest.yaml)
    CURATED_FUNCTIONS = [
        "tttrlib.TTTR",
        "tttrlib.TTTR.header",
        "tttrlib.TTTR.get_time_window_ranges",
        "tttrlib.Correlator",
        "tttrlib.CLSMImage",
        "tttrlib.CLSMImage.compute_ics",
        "tttrlib.TTTR.write",
    ]

    def __init__(self):
        """Initialize TttrlibAdapter."""
        pass

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover tttrlib functions from manual schemas.

        Since tttrlib uses SWIG bindings, we don't introspect. Instead,
        we return metadata based on the curated API defined in manifest.yaml.

        Args:
            module_config: Configuration from manifest

        Returns:
            List of FunctionMetadata (empty - schemas come from manifest)
        """
        # Return empty list - tttrlib uses fully manual schemas in manifest.yaml
        # The registry loads functions directly from the manifest
        return []

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern from function name.

        Args:
            func_name: Name of the function
            signature: Function signature (unused for tttrlib)

        Returns:
            Categorized I/O pattern
        """
        if func_name == "tttrlib.TTTR":
            return IOPattern.FILE_TO_REF  # Opens file, returns TTTRRef
        if func_name == "tttrlib.TTTR.header":
            return IOPattern.REF_TO_JSON  # Extracts metadata
        if func_name == "tttrlib.Correlator":
            return IOPattern.REF_TO_TABLE  # Correlation -> TableRef
        if func_name == "tttrlib.CLSMImage":
            return IOPattern.REF_TO_OBJECT  # Creates CLSMImage object
        if func_name == "tttrlib.CLSMImage.compute_ics":
            return IOPattern.OBJECT_TO_IMAGE  # ICS -> BioImageRef
        if func_name == "tttrlib.TTTR.get_time_window_ranges":
            return IOPattern.REF_TO_TABLE
        if func_name == "tttrlib.TTTR.write":
            return IOPattern.REF_TO_FILE
        return IOPattern.GENERIC

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance.

        Args:
            module_name: Name of the module
            func_name: Name of the function

        Returns:
            DimensionRequirement or None (tttrlib works with photon streams, not images)
        """
        # tttrlib operates on photon streams, not dimensional image data
        # No dimension hints needed
        return None
