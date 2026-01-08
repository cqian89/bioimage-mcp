"""
PhasorPy adapter for dynamic function registry.

Provides integration with phasorpy library for FLIM phasor analysis.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

# Setup logger
logger = logging.getLogger(__name__)


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

    def _assert_read_allowed(self, path: Path) -> None:
        """Enforce filesystem allowlist for reads using environment variable."""
        import json
        import os

        allowlist = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_READ")
        if not allowlist:
            return

        try:
            roots = json.loads(allowlist)
        except json.JSONDecodeError:
            return

        target = path.expanduser().absolute()
        for root in roots:
            root_path = Path(root).expanduser().absolute()
            try:
                target.relative_to(root_path)
                return
            except ValueError:
                continue

        raise PermissionError(f"Path not under any allowed read root: {target}")

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
                logger.debug("Scanning module: %s", module_name)
            except ImportError:
                logger.warning("Could not import phasorpy module: %s", module_name)
                continue

            # Get include/exclude patterns from config
            include = module_config.get("include", [])
            exclude = module_config.get("exclude", [])

            # Use inspect.getmembers to find all functions in the module
            for func_name, func in inspect.getmembers(module, inspect.isfunction):
                # Filter: no private functions, no tests
                if func_name.startswith("_") or func_name.startswith("test_"):
                    continue

                # Filter by include/exclude if provided
                if include and func_name not in include:
                    continue
                if exclude and func_name in exclude:
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

        # PHASOR_TRANSFORM: phasor_transform
        if func_name == "phasor_transform":
            return IOPattern.PHASOR_TRANSFORM

        # PHASOR_CALIBRATE: phasor_calibrate (needs 5 inputs including reference arrays)
        if func_name == "phasor_calibrate":
            return IOPattern.PHASOR_CALIBRATE

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
            uri = artifact.get("uri")
            path = artifact.get("path")
            metadata = artifact.get("metadata") or {}
            fmt = artifact.get("format")
        else:
            uri = getattr(artifact, "uri", None)
            path = getattr(artifact, "path", None)
            metadata = getattr(artifact, "metadata", {}) or {}
            fmt = getattr(artifact, "format", None)

        if not uri and not path:
            raise ValueError(f"Artifact missing both URI and path: {artifact}")

        if uri and str(uri).startswith("mem://"):
            # Handle mem:// URIs by checking metadata for _simulated_path
            path = metadata.get("_simulated_path")
            if not path:
                raise ValueError(
                    f"Cannot load mem:// URI without _simulated_path in metadata: {uri}"
                )
        elif uri:
            # Parse URI and get file path
            parsed = urlparse(str(uri))
            path = unquote(parsed.path)
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
        else:
            # Only path is present
            path = str(Path(path).absolute())

        # T041: Enforce filesystem allowlist for reads
        self._assert_read_allowed(Path(path))

        from bioio import BioImage

        reader = None
        if fmt == "OME-TIFF":
            try:
                from bioio_ome_tiff import Reader as OmeTiffReader

                reader = OmeTiffReader
            except ImportError:
                pass
        elif fmt == "TIFF":
            try:
                from bioio_tifffile import Reader as TiffReader

                reader = TiffReader
            except ImportError:
                pass
        elif fmt == "OME-Zarr":
            try:
                from bioio_ome_zarr import Reader as OmeZarrReader

                reader = OmeZarrReader
            except ImportError:
                pass

        try:
            img = BioImage(str(path), reader=reader)
        except Exception as first_error:
            if reader is not None:
                # Fallback: let BioImage auto-detect the reader
                logger.warning(
                    "Format-specific reader failed for %s (%s), falling back to auto-detection: %s",
                    path,
                    fmt,
                    first_error,
                )
                img = BioImage(str(path))
            else:
                raise

        # Use native dimensions (like skimage adapter)
        try:
            data = img.reader.xarray_data.values
        except (AttributeError, Exception):
            data = img.reader.data

        if hasattr(data, "compute"):
            data = data.compute()
        return data

    def _save_image(
        self,
        array: np.ndarray,
        work_dir: Path | None = None,
        name: str = "output",
        axes: str | None = None,  # Changed from "TCZYX"
        extra_metadata: dict[str, Any] | None = None,
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

        # Infer axes from array dimensions if not provided
        if axes is None:
            axes_map = {2: "YX", 3: "ZYX", 4: "CZYX", 5: "TCZYX"}
            axes = axes_map.get(array.ndim, "TCZYX"[-array.ndim :])

        # Ensure array has same number of dimensions as axes
        if array.ndim < len(axes):
            for _ in range(len(axes) - array.ndim):
                array = np.expand_dims(array, axis=0)
        elif array.ndim > len(axes):
            # This shouldn't happen with TCZYX usually, but if it does, we take the last ones
            axes = "TCZYX"[-array.ndim :] if array.ndim <= 5 else "ABCDE"[: array.ndim]

        from bioio.writers import OmeTiffWriter

        OmeTiffWriter.save(array, str(path), dim_order=axes)

        metadata = {
            "axes": axes,
            "dims": list(axes),
            "shape": list(array.shape),
            "ndim": array.ndim,
            "dtype": str(array.dtype),
            "output_name": name.split("-")[-1] if "-" in name else name,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        return {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "uri": path.absolute().as_uri(),
            "path": str(path.absolute()),
            "metadata": metadata,
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
        logger.info("Executing phasorpy function: %s", fn_id)
        try:
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
                raise RuntimeError(f"Could not load function {fn_id}: {e}") from e

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
                # Skip if artifact is a plain string that looks like metadata (not a ref_id)
                if isinstance(artifact, str) and (" " in artifact or len(artifact) > 64):
                    continue
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

            # Prepare metadata for output (T026, T039)
            extra_metadata = {}
            try:
                import phasorpy

                extra_metadata["phasorpy_version"] = getattr(phasorpy, "__version__", "unknown")
            except ImportError:
                pass

            # Include parameters in metadata
            if params:
                extra_metadata["parameters"] = params
                # Also flatten common ones for easier access
                if "frequency" in params:
                    extra_metadata["frequency"] = params["frequency"]
                if "harmonic" in params:
                    extra_metadata["harmonic"] = params["harmonic"]

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

                        outputs.append(
                            self._save_image(
                                item,
                                work_dir,
                                f"{func_name}-{name_hint}",
                                extra_metadata=extra_metadata,
                            )
                        )
            elif isinstance(result, np.ndarray) and not is_plot:
                outputs.append(
                    self._save_image(
                        result, work_dir, f"{func_name}-output", extra_metadata=extra_metadata
                    )
                )
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

                    # Convert to dict for JSON serialization in worker entrypoint
                    plot_dict = plot_ref.model_dump()
                    # Ensure we have path and uri for server import
                    plot_dict["path"] = str(path.absolute())
                    plot_dict["uri"] = path.absolute().as_uri()
                    outputs.append(plot_dict)

                    # Clean up to avoid figure accumulation
                    plt.close(fig)

            logger.info("Execution successful for %s, produced %d outputs", fn_id, len(outputs))
            return outputs

        except (ValueError, IndexError) as e:
            logger.error("Invalid parameter in %s: %s", fn_id, e)
            new_e = ValueError(f"Invalid parameter: {e}")
            new_e.code = "INVALID_PARAMETER"
            raise new_e from e
        except FileNotFoundError as e:
            logger.error("Artifact not found during %s: %s", fn_id, e)
            new_e = FileNotFoundError(f"Artifact not found: {e}")
            new_e.code = "ARTIFACT_NOT_FOUND"
            raise new_e from e
        except TypeError as e:
            logger.error("Invalid input type in %s: %s", fn_id, e)
            new_e = TypeError(f"Invalid input type: {e}")
            new_e.code = "INVALID_INPUT_TYPE"
            raise new_e from e
        except Exception as e:
            logger.error("Execution failed for %s: %s", fn_id, e)
            if hasattr(e, "code"):
                raise e
            new_e = RuntimeError(f"Execution failed: {e}")
            new_e.code = "EXECUTION_FAILED"
            raise new_e from e

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
