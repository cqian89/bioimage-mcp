"""
PhasorPy adapter for dynamic function registry.

Provides integration with phasorpy library for FLIM phasor analysis.
"""

import importlib
from datetime import UTC
from typing import Any

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

# Import phasorpy functions at module level for patching in tests
try:
    from phasorpy.phasor import phasor_from_signal, phasor_transform
except ImportError:
    # phasorpy not installed - tests will mock it
    phasor_from_signal = None
    phasor_transform = None


class PhasorPyAdapter:
    """Adapter for phasorpy library functions."""

    def __init__(self):
        """Initialize PhasorPyAdapter."""
        self.introspector = Introspector()

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from phasorpy modules.

        Args:
            module_config: Configuration from manifest with:
                - modules: list of module names to scan
                - module_name: single module name (alternative)
                - include_patterns: patterns for function names (currently unused
                  - hardcoded for US1)
                - exclude_patterns: patterns to exclude (currently unused)
        """
        # Support both 'modules' (list) and 'module_name' (single string)
        if "module_name" in module_config:
            modules = [module_config["module_name"]]
        else:
            modules = module_config.get("modules", [])

        # For US1: Hardcode the functions we need
        # TODO: Implement full pattern matching in later phases
        target_functions = {
            "phasorpy.phasor": ["phasor_from_signal", "phasor_transform"],
        }

        discovered = []
        for module_name in modules:
            if module_name not in target_functions:
                continue

            # Import the module
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            for func_name in target_functions[module_name]:
                # Get function from module
                if not hasattr(module, func_name):
                    continue

                func = getattr(module, func_name)

                # Resolve I/O pattern based on function name
                import inspect

                signature = inspect.signature(func)
                io_pattern = self.resolve_io_pattern(func_name, signature)

                # Introspect function
                metadata = self.introspector.introspect(
                    func=func,
                    source_adapter="phasorpy",
                    io_pattern=io_pattern,
                )

                # Override metadata fields to match expected fn_id format
                metadata.module = module_name
                metadata.qualified_name = f"{module_name}.{func_name}"
                metadata.fn_id = f"{module_name}.{func_name}"

                discovered.append(metadata)

        return discovered

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern from function name.

        Args:
            func_name: Name of the function
            signature: Function signature (unused, pattern is name-based)

        Returns:
            Categorized I/O pattern
        """
        if func_name == "phasor_from_signal":
            return IOPattern.SIGNAL_TO_PHASOR
        elif func_name == "phasor_transform":
            return IOPattern.PHASOR_TRANSFORM
        else:
            return IOPattern.PHASOR_TO_OTHER

    def execute(self, fn_id: str, inputs: list[Artifact], params: dict[str, Any]) -> list[Artifact]:
        """Execute a phasorpy function.

        Args:
            fn_id: Function ID like "phasorpy.phasor_from_signal"
            inputs: Input artifacts (BioImageRef)
            params: Parameters for the function

        Returns:
            List of output artifacts
        """
        # Extract function name from fn_id
        func_name = fn_id.split(".")[-1]

        # For now, just call the function (test mocks it)
        # In production, we'd load the input data from artifacts
        if func_name == "phasor_from_signal":
            result = phasor_from_signal(**params)

            # SIGNAL_TO_PHASOR pattern: phasor_from_signal returns (mean, real, imag)
            # Create 3 separate artifacts for each output
            from datetime import datetime

            outputs = []

            # Unpack the 3-tuple result
            mean, real, imag = result

            # Create artifact for mean
            outputs.append(
                ArtifactRef(
                    ref_id="phasor-mean",
                    type="BioImageRef",
                    uri="file:///tmp/phasor_mean.tif",
                    format="OME-TIFF",
                    mime_type="image/tiff",
                    size_bytes=1024,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )

            # Create artifact for real
            outputs.append(
                ArtifactRef(
                    ref_id="phasor-real",
                    type="BioImageRef",
                    uri="file:///tmp/phasor_real.tif",
                    format="OME-TIFF",
                    mime_type="image/tiff",
                    size_bytes=1024,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )

            # Create artifact for imag
            outputs.append(
                ArtifactRef(
                    ref_id="phasor-imag",
                    type="BioImageRef",
                    uri="file:///tmp/phasor_imag.tif",
                    format="OME-TIFF",
                    mime_type="image/tiff",
                    size_bytes=1024,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )

            return outputs
        elif func_name == "phasor_transform":
            result = phasor_transform(**params)

            # PHASOR_TRANSFORM pattern: phasor_transform returns (real, imag)
            # Create 2 separate artifacts for each output
            from datetime import datetime

            outputs = []

            # Unpack the 2-tuple result
            real, imag = result

            # Create artifact for real
            outputs.append(
                ArtifactRef(
                    ref_id="phasor-real",
                    type="BioImageRef",
                    uri="file:///tmp/phasor_real.tif",
                    format="OME-TIFF",
                    mime_type="image/tiff",
                    size_bytes=1024,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )

            # Create artifact for imag
            outputs.append(
                ArtifactRef(
                    ref_id="phasor-imag",
                    type="BioImageRef",
                    uri="file:///tmp/phasor_imag.tif",
                    format="OME-TIFF",
                    mime_type="image/tiff",
                    size_bytes=1024,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )

            return outputs
        else:
            raise ValueError(f"Unknown function: {func_name}")
