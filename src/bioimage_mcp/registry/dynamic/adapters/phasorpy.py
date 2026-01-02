"""
PhasorPy adapter for dynamic function registry.

Provides integration with phasorpy library for FLIM phasor analysis.
"""

from __future__ import annotations

import importlib
import inspect
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
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
                - include_patterns: patterns for function names (currently unused)
                - exclude_patterns: patterns to exclude (currently unused)
        """
        # Support both 'modules' (list) and 'module_name' (single string)
        if "module_name" in module_config:
            modules = [module_config["module_name"]]
        else:
            modules = module_config.get("modules", [])

        discovered = []
        for module_name in modules:
            # Skip phasorpy.io as per constitution (external I/O)
            if module_name == "phasorpy.io":
                continue

            # Import the module
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            # Use inspect.getmembers to find all functions in the module
            for func_name, func in inspect.getmembers(module, inspect.isfunction):
                # Filter: no private functions, no tests
                if func_name.startswith("_") or func_name.startswith("test_"):
                    continue

                # Ensure function belongs to phasorpy package
                if not getattr(func, "__module__", "").startswith("phasorpy"):
                    continue

                # Resolve I/O pattern
                io_pattern = self.resolve_io_pattern(func_name, module_name)

                # Introspect function
                metadata = self.introspector.introspect(
                    func=func,
                    source_adapter="phasorpy",
                    io_pattern=io_pattern,
                )

                # Override metadata fields to match expected fn_id format
                # Ensure module is the full name, not just the last part (introspector default)
                metadata.module = module_name
                metadata.qualified_name = f"{module_name}.{func_name}"
                metadata.fn_id = f"{module_name}.{func_name}"

                # Add dimension hints
                metadata.hints = self.generate_dimension_hints(module_name, func_name)

                discovered.append(metadata)

        return discovered

    def resolve_io_pattern(self, func_name: str, module_name: str) -> IOPattern:
        """Resolve I/O pattern from function name and module.

        Args:
            func_name: Name of the function
            module_name: Name of the module

        Returns:
            Categorized I/O pattern
        """
        # PLOT: functions in phasorpy.plot module or with "plot" in name
        if "phasorpy.plot" in module_name or "plot" in func_name.lower():
            return IOPattern.PLOT

        # SIGNAL_TO_PHASOR: phasor_from_signal
        if func_name == "phasor_from_signal":
            return IOPattern.SIGNAL_TO_PHASOR

        # PHASOR_TRANSFORM: phasor_transform, phasor_calibrate
        if func_name in ("phasor_transform", "phasor_calibrate"):
            return IOPattern.PHASOR_TRANSFORM

        # PHASOR_TO_SCALAR: phasor_to_apparent_lifetime, phasor_to_polar
        if "to_apparent_lifetime" in func_name or "to_polar" in func_name:
            return IOPattern.PHASOR_TO_SCALAR

        # SCALAR_TO_PHASOR: phasor_from_lifetime, phasor_from_polar
        if "from_lifetime" in func_name or "from_polar" in func_name:
            return IOPattern.SCALAR_TO_PHASOR

        # DEFAULT
        if "phasor" in func_name:
            return IOPattern.PHASOR_TO_OTHER

        return IOPattern.GENERIC

    def _load_image(self, artifact: Artifact) -> np.ndarray:
        """Load image data from artifact reference."""
        if isinstance(artifact, dict):
            uri = artifact.get("uri") or artifact.get("path") or ""
            metadata = artifact.get("metadata") or {}
            fmt = artifact.get("format")
        else:
            uri = getattr(artifact, "uri", None) or getattr(artifact, "path", None) or ""
            metadata = getattr(artifact, "metadata", {}) or {}
            fmt = getattr(artifact, "format", None)

        if not uri:
            raise ValueError(f"Artifact missing URI: {artifact}")

        # Handle mem:// URIs by checking metadata for _simulated_path
        if str(uri).startswith("mem://"):
            path = metadata.get("_simulated_path")
            if not path:
                raise ValueError(
                    f"Cannot load mem:// URI without _simulated_path in metadata: {uri}"
                )
        else:
            # Parse URI and get file path
            parsed = urlparse(str(uri))
            path = parsed.path
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]

        from bioio import BioImage

        reader = None
        if fmt == "OME-TIFF":
            try:
                from bioio_ome_tiff import Reader as OmeTiffReader

                reader = OmeTiffReader
            except ImportError:
                pass
        elif fmt == "OME-Zarr":
            try:
                from bioio_ome_zarr import Reader as OmeZarrReader

                reader = OmeZarrReader
            except ImportError:
                pass

        img = BioImage(str(path), reader=reader)
        data = img.data
        if hasattr(data, "compute"):
            data = data.compute()
        return data

    def _save_image(
        self,
        array: np.ndarray,
        work_dir: Path | None = None,
        name: str = "output",
        axes: str = "TCZYX",
    ) -> dict[str, Any]:
        """Save image array to file and return artifact reference dict."""
        ext = ".ome.tiff"
        if work_dir is None:
            fd, path_str = tempfile.mkstemp(suffix=ext)
            import os

            os.close(fd)
            path = Path(path_str)
        else:
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / f"{name}{ext}"

        # Ensure axes match dimensions
        if len(axes) > array.ndim:
            axes = axes[-array.ndim :]
        elif len(axes) < array.ndim:
            axes = "TCZYX"[-array.ndim :]

        from bioio.writers import OmeTiffWriter

        OmeTiffWriter.save(array, str(path), dim_order=axes)

        return {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "path": str(path.absolute()),
            "metadata": {
                "axes": axes,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
            },
        }

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact] | list[tuple[str, Artifact]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[Artifact]:
        """Execute a phasorpy function.

        Args:
            fn_id: Function ID like "phasorpy.phasor.phasor_from_signal"
            inputs: Input artifacts (BioImageRef)
            params: Parameters for the function
            work_dir: Optional working directory for execution

        Returns:
            List of output artifacts
        """
        # Parse fn_id to get module and function name
        parts = fn_id.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid fn_id: {fn_id}")

        module_name = ".".join(parts[:-1])
        func_name = parts[-1]

        # Import module and get function dynamically
        try:
            module = importlib.import_module(module_name)
            target_fn = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise RuntimeError(f"Could not load function {fn_id}: {e}")

        # Match inputs to function parameters
        sig = inspect.signature(target_fn)
        bound_args = {}

        # Handle inputs
        # If inputs is a list of tuples (name, artifact), use it
        input_items = []
        if inputs and isinstance(inputs[0], tuple):
            input_items = inputs
        else:
            # Match by order for positional parameters
            # PhasorPy functions usually take arrays as their first arguments
            param_names = [
                p.name
                for p in sig.parameters.values()
                if p.kind
                in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            for i, art in enumerate(inputs):
                if i < len(param_names):
                    input_items.append((param_names[i], art))

        # Load image data for all artifact inputs
        for name, artifact in input_items:
            bound_args[name] = self._load_image(artifact)

        # Add other parameters
        for name, value in params.items():
            if name in sig.parameters:
                bound_args[name] = value

        # Execute
        # Handle positional-only arguments correctly
        pos_args = []
        kw_args = {}
        for param in sig.parameters.values():
            if param.name in bound_args:
                if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    pos_args.append(bound_args[param.name])
                else:
                    kw_args[param.name] = bound_args[param.name]

        # Prepare execution environment for plots
        is_plot = "phasorpy.plot" in module_name or "plot" in func_name.lower()
        if is_plot:
            import matplotlib

            matplotlib.use("Agg")  # T020: Use Agg backend for headless plot capture

        result = target_fn(*pos_args, **kw_args)

        # Handle outputs
        outputs = []
        if isinstance(result, tuple) and not is_plot:
            for i, item in enumerate(result):
                if isinstance(item, np.ndarray):
                    # Try to give a meaningful name
                    name_hint = f"output-{i}"
                    if func_name == "phasor_from_signal" and i < 3:
                        name_hint = ["mean", "real", "imag"][i]
                    elif "phasor" in func_name and len(result) == 2 and i < 2:
                        name_hint = ["real", "imag"][i]

                    outputs.append(self._save_image(item, work_dir, f"{func_name}-{name_hint}"))
        elif isinstance(result, np.ndarray) and not is_plot:
            outputs.append(self._save_image(result, work_dir, f"{func_name}-output"))
        elif is_plot:
            # Handle plot functions - they might return a figure or axis
            import matplotlib.pyplot as plt

            from bioimage_mcp.artifacts.store import write_plot

            fig = plt.gcf()
            if fig:
                ext = ".png"
                if work_dir:
                    path = work_dir / f"{func_name}-plot{ext}"
                else:
                    fd, path_str = tempfile.mkstemp(suffix=ext)
                    import os

                    os.close(fd)
                    path = Path(path_str)

                # T022: Connect PlotRef creation to write_plot()
                plot_ref = write_plot(fig, path, dpi=100, plot_type=func_name)
                outputs.append(plot_ref)

                # Clean up to avoid figure accumulation
                plt.close(fig)

        return outputs

    def generate_dimension_hints(self, module_name: str, func_name: str) -> Any | None:
        """Generate dimension hints for agent guidance."""
        # Use local imports to avoid circular dependencies if any
        from bioimage_mcp.api.schemas import (
            DimensionRequirement,
            FunctionHints,
            InputRequirement,
        )

        if func_name == "phasor_from_signal":
            return FunctionHints(
                inputs={
                    "signal": InputRequirement(
                        type="BioImageRef",
                        required=True,
                        description="Input signal array (decay or spectrum)",
                        dimension_requirements=DimensionRequirement(
                            preprocessing_instructions=[
                                "Ensure the decay/spectrum dimension is at axis -1"
                            ],
                            expected_axes=["T", "C", "Z", "Y", "X"],
                        ),
                    )
                }
            )

        if "phasorpy.filter" in module_name:
            return FunctionHints(
                inputs={
                    "real": InputRequirement(
                        type="BioImageRef",
                        required=True,
                        description="Real part of phasor",
                        dimension_requirements=DimensionRequirement(spatial_axes=["Y", "X"]),
                    ),
                    "imag": InputRequirement(
                        type="BioImageRef",
                        required=True,
                        description="Imaginary part of phasor",
                        dimension_requirements=DimensionRequirement(spatial_axes=["Y", "X"]),
                    ),
                }
            )

        return None
