"""
PhasorPy adapter for dynamic function registry.

Provides integration with phasorpy library for FLIM phasor analysis.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

# Setup logger
logger = logging.getLogger(__name__)


# Parameters that are artifact inputs, not schema params
# This prevents them from appearing in the MCP tools params_schema
# as scalar "number" types when they should be passed as BioImageRef/inputs.
ARTIFACT_INPUT_PARAMS = {
    "signal",  # phasor_from_signal primary input
    "real",  # phasor coordinate arrays
    "imag",  # phasor coordinate arrays
    "mean",  # mean intensity image
    "reference_real",  # calibration reference
    "reference_imag",  # calibration reference
    "measured_real",  # calibration measured
    "measured_imag",  # calibration measured
    "phase",  # polar coordinates
    "modulation",  # polar coordinates
    "image",  # general image input
    "data",  # generic data input
    "phasor_real",  # alternative naming
    "phasor_imag",  # alternative naming
}


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

                # Filter out parameters that are artifact inputs, not schema params
                # This prevents them from appearing in the MCP tools params_schema
                metadata.parameters = {
                    p_name: p_schema
                    for p_name, p_schema in metadata.parameters.items()
                    if p_name not in ARTIFACT_INPUT_PARAMS
                }

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
        # PHASOR_PLOT: plot_phasor needs real/imag inputs
        if func_name == "plot_phasor":
            return IOPattern.PHASOR_PLOT

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

        # Handle ObjectRef input
        if uri and str(uri).startswith("obj://"):
            if uri not in OBJECT_CACHE:
                raise ValueError(f"Object with URI {uri} not found in memory cache")
            return OBJECT_CACHE[uri]

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

        # If metadata suggests fewer axes than data.ndim, and we have
        # singleton dimensions, squeeze (like SkimageAdapter)
        expected_axes = metadata.get("axes")
        if expected_axes and len(expected_axes) < data.ndim:
            squeezed = np.squeeze(data)
            if squeezed.ndim == len(expected_axes):
                logger.debug(
                    "Squeezed data from %d to %d dimensions to match expected axes: %s",
                    data.ndim,
                    squeezed.ndim,
                    expected_axes,
                )
                data = squeezed

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
        # Coerce axes to string if it's a list of single-char strings
        if isinstance(axes, list):
            if all(isinstance(a, str) and len(a) == 1 for a in axes):
                axes = "".join(axes)
            else:
                axes = None  # Invalid format, let inference handle it

        ext = ".ome.tiff"
        if work_dir is None:
            fd, path_str = tempfile.mkstemp(suffix=ext)
            import os

            os.close(fd)
            path = Path(path_str)
        else:
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / f"{name}{ext}"

        # Only use passed axes if they match the output array dimensions (inheritance)
        if axes and len(axes) == array.ndim:
            inferred_axes = axes
        else:
            # Infer axes from array dimensions
            axes_map = {2: "YX", 3: "ZYX", 4: "CZYX", 5: "TCZYX"}
            if array.ndim in axes_map:
                inferred_axes = axes_map[array.ndim]
            else:
                if array.ndim > 6:
                    raise ValueError(
                        f"Cannot infer axes for {array.ndim}D array (max 6 dimensions supported). "
                        "Provide explicit axes metadata."
                    )
                inferred_axes = (
                    "TCZYX"[-array.ndim :] if array.ndim <= 5 else "STCZYX"[: array.ndim]
                )

        axes = inferred_axes

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
                    elif param.kind not in (
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    ):
                        kw_args[param.name] = bound_args[param.name]

            # Prepare execution environment for plots
            is_plot = "phasorpy.plot" in module_name or "plot" in func_name.lower()
            ax_from_params = False
            _ax_from_figure = False
            _fig_from_inputs = None

            if is_plot:
                import matplotlib

                matplotlib.use("Agg")  # T020: Use Agg backend for headless plot capture

                # Check for ax/axes in params and resolve from cache
                for ax_name in ("ax", "axes"):
                    if ax_name in params:
                        ax_ref = params[ax_name]
                        resolved_ax = None
                        # Resolve ObjectRef/AxesRef from cache
                        if isinstance(ax_ref, dict) and ax_ref.get("uri", "").startswith("obj://"):
                            uri = ax_ref["uri"]
                            if uri in OBJECT_CACHE:
                                resolved_ax = OBJECT_CACHE[uri]
                            else:
                                raise ValueError(
                                    f"AxesRef with URI '{uri}' not found in object cache"
                                )
                        elif ax_ref is not None and not isinstance(ax_ref, dict):
                            # Already a matplotlib axes object (shouldn't happen in MCP
                            # but handle it)
                            resolved_ax = ax_ref

                        if resolved_ax is not None:
                            # Force parameter name to 'ax' as per PhasorPy convention
                            kw_args["ax"] = resolved_ax
                            ax_from_params = True

                            # Clean up: if 'axes' was the param name and exists
                            # unresolved, remove it
                            if ax_name == "axes" and "axes" in kw_args:
                                del kw_args["axes"]
                            break  # Found and resolved, no need to check other names

                # Compatibility: base.phasorpy.plot.plot_phasor is declared with a required
                # 'figure' input in our manifest/registry ports. Historically this input was
                # ignored, causing plot_phasor to create its own internal figure.
                #
                # That breaks the common workflow:
                # subplots() -> plot_phasor() -> Figure.savefig() (blank axes-only output).
                #
                # If no explicit ax/axes param was provided, but a FigureRef/ObjectRef was
                # provided as an input named 'figure', plot on its first axes.
                if func_name == "plot_phasor" and not ax_from_params and "ax" not in kw_args:
                    fig_obj = bound_args.get("figure") or bound_args.get("fig")
                    if fig_obj is not None:
                        try:
                            from matplotlib.figure import Figure

                            if isinstance(fig_obj, Figure):
                                _fig_from_inputs = fig_obj
                                if fig_obj.axes:
                                    kw_args["ax"] = fig_obj.axes[0]
                                else:
                                    kw_args["ax"] = fig_obj.add_subplot(1, 1, 1)
                                _ax_from_figure = True
                                logger.debug(
                                    "plot_phasor called without ax; "
                                    "using axes from provided figure input"
                                )
                        except Exception:  # noqa: BLE001
                            # If anything goes wrong, fall back to phasorpy's default behavior
                            # (create an internal figure).
                            pass

            result = target_fn(*pos_args, **kw_args)

            # Prepare metadata for output (T026, T039)
            extra_metadata = {}

            # Extract axes from primary input for inheritance
            input_axes = None
            for _name, artifact in input_items:
                if isinstance(artifact, dict):
                    input_axes = artifact.get("metadata", {}).get("axes")
                else:
                    input_axes = getattr(artifact, "metadata", {}).get("axes")
                if input_axes:
                    break

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
                                axes=input_axes,
                                extra_metadata=extra_metadata,
                            )
                        )
            elif isinstance(result, np.ndarray) and not is_plot:
                outputs.append(
                    self._save_image(
                        result,
                        work_dir,
                        f"{func_name}-output",
                        axes=input_axes,
                        extra_metadata=extra_metadata,
                    )
                )
            elif is_plot:
                import matplotlib.pyplot as plt

                # Get the current figure (phasorpy draws on it)
                fig = plt.gcf()

                # Generate FigureRef
                fig_id = str(uuid.uuid4())
                session_id = "default"  # Could be passed in via context
                env_id = "base"
                fig_uri = f"obj://{session_id}/{env_id}/{fig_id}"

                fig._mcp_ref_id = fig_id
                OBJECT_CACHE[fig_uri] = fig

                # Detect if figure is empty (no content drawn)
                has_content = False
                for ax in fig.axes:
                    if ax.lines or ax.collections or ax.images or ax.patches or ax.texts:
                        has_content = True
                        break

                fig_metadata = {
                    "output_name": "figure",
                    "figsize": fig.get_size_inches().tolist(),
                    "dpi": int(fig.get_dpi()),
                    "axes_count": len(fig.axes),
                    "is_empty": not has_content,
                }

                if not has_content:
                    fig_metadata["warning"] = "Figure appears empty - no data was plotted"

                fig_ref = {
                    "ref_id": fig_id,
                    "type": "FigureRef",
                    "python_class": "matplotlib.figure.Figure",
                    "uri": fig_uri,
                    "storage_type": "memory",
                    "metadata": fig_metadata,
                }
                outputs.append(fig_ref)

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
                            min_ndim=2,
                            preprocessing_instructions=[
                                "Ensure the decay/spectrum dimension is at axis -1"
                            ],
                            # Don't force 5D, allow any dimensionality where axis -1 is signal
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
