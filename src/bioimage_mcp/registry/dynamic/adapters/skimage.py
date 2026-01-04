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
from urllib.parse import urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

try:
    import tifffile
except ImportError:
    tifffile = None


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
                meta = self.introspector.introspect(
                    func=obj,
                    source_adapter="skimage",
                    io_pattern=io_pattern,
                )
                meta.module = mod_name
                meta.qualified_name = f"{mod_name}.{name}"
                meta.fn_id = f"{mod_name}.{name}"

                # Add dimension hints (T203)
                dim_hints = self.generate_dimension_hints(mod_name, name)
                if dim_hints:
                    from bioimage_mcp.api.schemas import FunctionHints, InputRequirement

                    # Populate hints for the primary image input
                    # Most skimage functions take the image as the first argument
                    # We'll use the name discovered by introspector
                    param_names = list(meta.parameters.keys())
                    if param_names:
                        first_param = param_names[0]
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
        if func_name.startswith("threshold_"):
            return IOPattern.ARRAY_TO_SCALAR
        if func_name.startswith("is_"):
            return IOPattern.ARRAY_TO_SCALAR

        # Module-level defaults
        if "segmentation" in module_name:
            return IOPattern.IMAGE_TO_LABELS
        if "measure" in module_name:
            return IOPattern.LABELS_TO_TABLE
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
            uri = artifact["uri"]
            fmt = artifact.get("format")
        else:
            uri = artifact.uri
            fmt = getattr(artifact, "format", None)

        # Parse URI and get file path
        parsed = urlparse(uri)
        path = parsed.path
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]

        # Use bioio if available for consistent 5D loading (P0 requirement)
        try:
            from bioio import BioImage

            reader = None
            if fmt == "OME-TIFF":
                from bioio_ome_tiff import Reader as OmeTiffReader

                reader = OmeTiffReader
            elif fmt == "OME-Zarr":
                from bioio_ome_zarr import Reader as OmeZarrReader

                reader = OmeZarrReader

            img = BioImage(path, reader=reader)
            # Use native dimensions (T020)
            data = img.reader.data
            if hasattr(data, "compute"):
                data = data.compute()

            if data is not None and data.size > 0:
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
            "path": str(path.absolute()),
        }

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
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

        # Load input images
        args = []
        kwargs: dict[str, Any] = {}
        param_names = set(inspect.signature(func).parameters.keys())
        for name, artifact in self._normalize_inputs(inputs):
            image_data = self._load_image(artifact)
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

        # Save result and create artifact reference dict
        io_pattern = self.determine_io_pattern(module_path, func_name)
        if io_pattern == IOPattern.LABELS_TO_TABLE:
            if not isinstance(result, dict):
                raise ValueError("Expected table dict output for labels_to_table function")
            output_ref = self._save_table(result, work_dir=work_dir)
        else:
            axes = ""
            for _, artifact in self._normalize_inputs(inputs):
                axes = self._extract_axes(artifact)
                if axes:
                    break
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
