"""
Adapter for scikit-image functions.
"""

from __future__ import annotations

import csv
import importlib
import inspect
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

try:
    import tifffile
except ImportError:
    tifffile = None


# Parameters that are artifact inputs, not schema params
ARTIFACT_INPUT_PARAMS = {
    "image",
    "input",
    "labels",
    "label_image",
    "intensity_image",
    "input_image",
    "source",
    "src",
}


class SkimageAdapter(BaseAdapter):
    """Adapter for exposing scikit-image functions dynamically."""

    def __init__(self) -> None:
        self.introspector = Introspector()

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from configured modules."""
        module_name = module_config.get("module_name")
        if not module_name and "modules" in module_config:
            # Handle manifest format where modules is a list
            # We iterate one at a time, but here we might get called for each?
            # Or config is one entry from dynamic_sources?
            # DynamicSource has 'modules' list.
            # Let's assume module_config is ONE item from modules list if called iteratively,
            # OR DynamicSource dict.
            # discovery.py iterates modules.
            # Let's check discovery.py: it calls adapter.discover(source.model_dump()).
            # source.model_dump() has "modules": ["skimage.filters", ...]
            # So we iterate here.
            modules = module_config["modules"]
        else:
            modules = [module_name] if module_name else []

        results = []
        for mod_name in modules:
            try:
                module = importlib.import_module(mod_name)
            except ImportError:
                continue

            # Filter functions (simple logic for now, respecting include/exclude patterns
            # from config if passed)
            # For now, just getting public functions
            for name in dir(module):
                if name.startswith("_"):
                    continue
                obj = getattr(module, name)
                # Use inspect to filter only actual functions and builtins
                # This excludes PytestTester instances, classes, etc.
                if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
                    continue

                # Discovery should exclude methods with **kwargs unless overlay exists (T047)
                try:
                    sig = inspect.signature(obj)
                    if any(
                        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                    ):
                        continue
                except (ValueError, TypeError):
                    # Builtins might not have signatures
                    pass

                # Check inclusion (simple check if 'include' in config)
                include_patterns = (
                    module_config.get("include_patterns") or module_config.get("include") or ["*"]
                )
                # exclude_patterns = module_config.get("exclude_patterns", [])

                # Simple wildcard check
                if "*" not in include_patterns and name not in include_patterns:
                    continue

                # Introspect
                io_pattern = self.determine_io_pattern(mod_name, name)

                # Redirect regionprops schema to regionprops_table (Follow-up 1)
                is_regionprops_redirect = name == "regionprops" and mod_name == "skimage.measure"
                introspection_obj = obj
                if is_regionprops_redirect:
                    try:
                        # Introspect regionprops_table instead to get the correct schema
                        introspection_obj = getattr(module, "regionprops_table")
                    except AttributeError:
                        pass

                meta = self.introspector.introspect(
                    func=introspection_obj,
                    source_adapter="skimage",
                    io_pattern=io_pattern,
                )

                if is_regionprops_redirect:
                    # Restore the original name (which would be regionprops_table from introspection)
                    meta.name = name
                    meta.description = (
                        "NOTE: This function is redirected to regionprops_table for serializable output. "
                        + (meta.description or "")
                    )
                    # Ensure offset and coordinates are removed (if they were somehow present)
                    meta.parameters.pop("offset", None)
                    meta.parameters.pop("coordinates", None)

                # Keep original parameter names for hint generation before filtering
                all_param_names = list(meta.parameters.keys())

                # Filter out parameters that are artifact inputs, not schema params
                # This prevents them from appearing in the MCP tools params_schema
                meta.parameters = {
                    p_name: p_schema
                    for p_name, p_schema in meta.parameters.items()
                    if p_name not in ARTIFACT_INPUT_PARAMS
                }

                meta.module = mod_name
                meta.qualified_name = f"{mod_name}.{name}"
                meta.fn_id = f"{mod_name}.{name}"

                # Add dimension hints (T203)
                dim_hints = self.generate_dimension_hints(mod_name, name)
                if dim_hints:
                    from bioimage_mcp.api.schemas import FunctionHints, InputRequirement

                    # Populate hints for the primary image input
                    # Most skimage functions take the image as the first argument
                    if all_param_names:
                        first_param = all_param_names[0]
                        meta.hints = FunctionHints(
                            inputs={
                                first_param: InputRequirement(
                                    type="BioImageRef",
                                    required=True,
                                    description=f"Input image for {name}",
                                    dimension_requirements=dim_hints,
                                )
                            }
                        )

                results.append(meta)
        return results

    def determine_io_pattern(self, module_name: str, func_name: str) -> IOPattern:
        """Determine I/O pattern based on module and function name."""
        # Function-level overrides
        if func_name == "label":
            return IOPattern.IMAGE_TO_LABELS
        if func_name.startswith("threshold_"):
            return IOPattern.ARRAY_TO_SCALAR
        if func_name.startswith("is_"):
            return IOPattern.ARRAY_TO_SCALAR

        # Module-level defaults
        if "segmentation" in module_name:
            return IOPattern.IMAGE_TO_LABELS
        if "measure" in module_name:
            if "table" in func_name:
                return IOPattern.LABELS_TO_TABLE
            # label, regionprops, etc.
            if func_name == "label":
                return IOPattern.IMAGE_TO_LABELS
            return IOPattern.LABELS_TO_TABLE  # Default for measure for now
        if "filters" in module_name:
            return IOPattern.IMAGE_TO_IMAGE

        # Generic default
        return IOPattern.IMAGE_TO_IMAGE

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern based on function name (legacy/protocol)."""
        # Best effort without module context
        return self.determine_io_pattern("", func_name)

    def _normalize_inputs(self, inputs: list[Artifact]) -> list[tuple[str, Artifact]]:
        normalized: list[tuple[str, Artifact]] = []
        for idx, item in enumerate(inputs):
            if isinstance(item, tuple) and len(item) == 2:
                name, artifact = item
            else:
                name = "image" if idx == 0 else f"input_{idx}"
                artifact = item
            normalized.append((str(name), artifact))
        return normalized

    def _load_image(self, artifact: Artifact) -> np.ndarray:
        """Load image data from artifact reference."""
        # Handle both dict and Pydantic model
        if isinstance(artifact, dict):
            uri = artifact.get("uri")
            path = artifact.get("path")
            fmt = artifact.get("format")
            metadata = artifact.get("metadata") or {}
        else:
            uri = getattr(artifact, "uri", None)
            path = getattr(artifact, "path", None)
            fmt = getattr(artifact, "format", None)
            metadata = getattr(artifact, "metadata", {}) or {}

        # Handle ObjectRef input (obj:// URIs are memory-backed)
        if uri and str(uri).startswith("obj://"):
            if uri not in OBJECT_CACHE:
                raise ValueError(f"Object with URI {uri} not found in memory cache")
            return OBJECT_CACHE[uri]

        if not uri and not path:
            raise ValueError(f"Artifact missing both URI and path: {artifact}")

        if uri:
            # Parse URI and get file path
            parsed = urlparse(uri)
            path = unquote(parsed.path)
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
        else:
            # Only path is present, convert to absolute path string
            path = str(Path(path).absolute())

        # Use bioio if available for consistent 5D loading (P0 requirement)
        try:
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

            img = BioImage(path, reader=reader)
            # Use native dimensions (T020)
            # reader.xarray_data provides native dimensions, whereas reader.data is always 5D
            try:
                data = img.reader.xarray_data.values
            except (AttributeError, Exception):
                data = img.reader.data

            if hasattr(data, "compute"):
                data = data.compute()

            if data is not None and data.size > 0:
                # If metadata suggests fewer axes than data.ndim, and we have
                # singleton dimensions, squeeze
                expected_axes = metadata.get("axes")
                if expected_axes and len(expected_axes) < data.ndim:
                    squeezed = np.squeeze(data)
                    if squeezed.ndim == len(expected_axes):
                        data = squeezed
                return data
        except Exception:
            pass

        if tifffile is None:
            raise RuntimeError("tifffile is required for loading images")

        # Fallback to tifffile but try to ensure it doesn't squeeze if it's OME-TIFF
        return tifffile.imread(path)

    def _extract_axes(self, artifact: Artifact) -> str:
        metadata: dict[str, Any] = {}
        if isinstance(artifact, dict):
            metadata = artifact.get("metadata") or {}
        else:
            metadata = getattr(artifact, "metadata", {}) or {}
        return str(metadata.get("axes") or "")

    def _infer_axes(self, array: np.ndarray) -> str:
        axes_map = {
            2: "YX",
            3: "ZYX",
            4: "CZYX",
            5: "TCZYX",
        }
        return axes_map.get(array.ndim, "")

    def _save_image(
        self,
        array: np.ndarray,
        work_dir: Path | None = None,
        axes: str | None = None,
    ) -> dict:
        """Save image array to file and return artifact reference dict."""
        # Use .ome.tiff extension for better compatibility
        ext = ".ome.tiff"

        if array.dtype == np.int64 or array.dtype == np.uint64:
            # OME-TIFF/tifffile doesn't support 64-bit ints in OME-XML
            array = array.astype(np.uint32)

        if work_dir is None:
            # Use system temp directory
            fd, path_str = tempfile.mkstemp(suffix=ext)
            import os

            os.close(fd)
            path = Path(path_str)
        else:
            # Use provided work directory
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / f"output{ext}"

        # Only use passed axes if they match the output array dimensions
        if axes and len(axes) == array.ndim:
            inferred_axes = axes
        else:
            inferred_axes = self._infer_axes(array)

        # Save image using OmeTiffWriter for consistency
        saved = False
        try:
            from bioio.writers import OmeTiffWriter

            if len(inferred_axes) == array.ndim:
                OmeTiffWriter.save(array, str(path), dim_order=inferred_axes)
                saved = True
        except Exception:
            pass

        if not saved:
            if tifffile is None:
                raise RuntimeError("tifffile is required for saving images")
            metadata = {"axes": inferred_axes} if inferred_axes else None
            tifffile.imwrite(path, array, metadata=metadata, photometric="minisblack")

        # Return artifact reference as dict (compatible with entrypoint protocol)
        ref = {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "uri": path.absolute().as_uri(),
            "path": str(path.absolute()),
            "metadata": {
                "axes": inferred_axes,
                "dims": list(inferred_axes) if inferred_axes else [],
                "ndim": array.ndim,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
            },
        }
        return ref

    def _save_table(self, table: dict, work_dir: Path | None = None) -> dict:
        if work_dir is None:
            fd, path_str = tempfile.mkstemp(suffix=".csv")
            import os

            os.close(fd)
            path = Path(path_str)
        else:
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / "output.csv"

        columns = list(table.keys())
        rows = []
        if columns:
            column_arrays = [np.asarray(table[col]).tolist() for col in columns]
            rows = list(zip(*column_arrays, strict=False))

        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)

        return {
            "type": "TableRef",
            "format": "csv",
            "uri": path.absolute().as_uri(),
            "path": str(path.absolute()),
        }

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
        hints: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Execute the function."""
        # fn_id = skimage.filters.gaussian
        parts = fn_id.split(".")
        if len(parts) < 3:
            raise ValueError(f"Invalid fn_id: {fn_id}")

        module_path = ".".join(parts[:-1])
        func_name = parts[-1]

        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # Transparently redirect regionprops -> regionprops_table (Task 1)
        notice = None
        if func_name == "regionprops" and "measure" in module_path:
            func_name = "regionprops_table"
            func = getattr(module, func_name)
            notice = "Redirected regionprops to regionprops_table for serializable output."

            # Map parameters
            params = params.copy()
            params.pop("offset", None)  # Not supported by regionprops_table
            params.pop("coordinates", None)  # Not supported by regionprops_table
            if "properties" not in params:
                params["properties"] = ["label", "area", "centroid", "bbox"]

        from bioimage_mcp.api.schemas import DimensionRequirement

        # Load input images

        args = []
        kwargs: dict[str, Any] = {}
        param_names = set(inspect.signature(func).parameters.keys())
        output_axes = ""
        channel_was_transposed = False
        original_axes = None
        for name, artifact in self._normalize_inputs(inputs):
            # Skip if artifact is a plain string that looks like metadata (not a ref_id)
            if isinstance(artifact, str) and (" " in artifact or len(artifact) > 64):
                continue

            # Resolve dimension requirements from hints (T048)
            req = None
            if hints:
                input_hints = hints.get("inputs", {})
                req_data = input_hints.get(name) or input_hints.get("image")
                if req_data:
                    dim_req_data = req_data.get("dimension_requirements")
                    if dim_req_data:
                        req = DimensionRequirement(**dim_req_data)

            image_data = self._load_image(artifact)

            # Get axes for this artifact to handle channel-last requirement
            axes = self._extract_axes(artifact)
            if not axes:
                axes = self._infer_axes(image_data)

            # Squeeze if requested (T048)
            if req and req.squeeze_singleton:
                # Update axes string to match squeezed dimensions
                if len(axes) == image_data.ndim:
                    axes = "".join(axes[i] for i, size in enumerate(image_data.shape) if size > 1)
                image_data = np.squeeze(image_data)
                # Fallback if axes mismatched or became empty
                if not axes or len(axes) != image_data.ndim:
                    axes = self._infer_axes(image_data)

            # Track original axes for restoring canonical order before save
            if original_axes is None:
                original_axes = axes

            # scikit-image expects channel-last format (Y, X, C)
            if "C" in axes:
                c_idx = axes.find("C")
                if c_idx != -1 and c_idx != image_data.ndim - 1:
                    # Move channel axis to the end for skimage compatibility
                    new_order = [i for i in range(image_data.ndim) if i != c_idx] + [c_idx]
                    image_data = np.transpose(image_data, new_order)
                    # Update axes to reflect the new order
                    axes = "".join(axes[i] for i in new_order)
                    channel_was_transposed = True

            # Capture axes from the first image-like input for output reference
            if not output_axes:
                output_axes = axes

            param_name = name
            if name == "labels" and "label_image" in param_names:
                param_name = "label_image"
            if param_name in {"label_image", "labels"} and not args:
                args.append(image_data)
                continue
            is_explicit_name = name != "image" and not name.startswith("input_")
            if is_explicit_name:
                kwargs[param_name] = image_data
                continue
            if param_name in param_names:
                kwargs[param_name] = image_data
            else:
                args.append(image_data)

        # Execute function
        result = func(*args, **kwargs, **params)

        # Restore channel-first order for OME-TIFF canonical output (T050)
        if (
            channel_was_transposed
            and isinstance(result, np.ndarray)
            and result.ndim == len(output_axes)
        ):
            # output_axes is channel-last (e.g., "YXC"), restore to original order
            # Find where C is in output_axes and move it back to its original position
            if "C" in output_axes:
                c_idx_out = output_axes.find("C")
                c_idx_orig = original_axes.find("C")
                if c_idx_out != c_idx_orig and c_idx_out != -1:
                    # Build the reverse transpose: move C from last to original position
                    # Current order: [other dims..., C], target: insert C at c_idx_orig
                    axes_list = list(output_axes)
                    axes_list.pop(c_idx_out)
                    axes_list.insert(c_idx_orig, "C")
                    # Build transpose order
                    current_positions = {ax: i for i, ax in enumerate(output_axes)}
                    new_order = [current_positions[ax] for ax in axes_list]
                    result = np.transpose(result, new_order)
                    output_axes = "".join(axes_list)

        # Save result and create artifact reference dict

        io_pattern = self.determine_io_pattern(module_path, func_name)
        if io_pattern == IOPattern.LABELS_TO_TABLE:
            if not isinstance(result, dict):
                raise ValueError("Expected table dict output for labels_to_table function")
            output_ref = self._save_table(result, work_dir=work_dir)
            if notice:
                if "metadata" not in output_ref:
                    output_ref["metadata"] = {}
                output_ref["metadata"]["notice"] = notice
        else:
            # Use processed axes from inputs if available, otherwise find first
            axes = output_axes
            if not axes:
                for _, artifact in self._normalize_inputs(inputs):
                    # Skip metadata
                    if isinstance(artifact, str) and (" " in artifact or len(artifact) > 64):
                        continue
                    axes = self._extract_axes(artifact)
                    if axes:
                        break
            # Use expand_if_required for OME-TIFF preservation (T045a)

            # For now, default to no specific output requirement unless hints
            # provided but OmeTiffWriter will expand anyway.
            # Here we just pass the result as is, _save_image handles expansion
            # to TCZYX if using OmeTiffWriter.
            output_ref = self._save_image(result, work_dir=work_dir, axes=axes)

        return [output_ref]

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        from bioimage_mcp.api.schemas import DimensionRequirement

        # Functions that require exactly 2D input
        require_2d = {
            "threshold_otsu",
            "threshold_li",
            "threshold_triangle",
            "threshold_isodata",
            "threshold_mean",
            "threshold_minimum",
            "threshold_yen",
            "felzenszwalb",
            "slic",
            "quickshift",
        }

        # Functions that accept 2D or 3D
        require_2d_or_3d = {
            "gaussian",
            "sobel",
            "canny",
            "erosion",
            "dilation",
            "opening",
            "closing",
            "median",
            "maximum",
            "minimum",
            "regionprops",
            "regionprops_table",
            "label",
        }

        if func_name in require_2d:
            return DimensionRequirement(
                min_ndim=2,
                max_ndim=2,
                expected_axes=["Y", "X"],
                squeeze_singleton=True,
                preprocessing_instructions=[
                    "Squeeze singleton T, C, Z dimensions first",
                    "If multiple channels, select one channel or convert to grayscale",
                    "If 3D stack, select a single Z slice",
                    "Use base.xarray.squeeze or base.xarray.isel for preprocessing",
                ],
            )

        if func_name in require_2d_or_3d:
            return DimensionRequirement(
                min_ndim=2,
                max_ndim=3,
                expected_axes=["Y", "X"],
                squeeze_singleton=True,
                preprocessing_instructions=[
                    "Squeeze singleton T and C dimensions first",
                    "Function supports 2D (YX) or 3D (ZYX) input",
                    "Use base.xarray.squeeze for preprocessing",
                ],
            )

        return None
