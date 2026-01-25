"""
Adapter for scipy.ndimage functions.
"""

from __future__ import annotations

import importlib
import inspect
import tempfile
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import yaml
from urllib.parse import unquote, urlparse

import numpy as np

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE
from bioimage_mcp.registry.dynamic.adapters.callable_registry import resolve_callable

logger = logging.getLogger(__name__)

try:
    import tifffile
except ImportError:
    tifffile = None


if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement


class ScipyNdimageAdapter(BaseAdapter):
    """Adapter for exposing scipy.ndimage functions dynamically."""

    def __init__(self) -> None:
        self.introspector = Introspector()

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from configured modules."""
        module_name = module_config.get("module_name")
        if not module_name and "modules" in module_config:
            modules = module_config["modules"]
        else:
            modules = [module_name] if module_name else []

        blacklist = set()
        blacklist_path = module_config.get("blacklist_path")
        manifest_path = module_config.get("_manifest_path")
        if blacklist_path and manifest_path:
            full_blacklist_path = Path(manifest_path).parent / blacklist_path
            if full_blacklist_path.exists():
                try:
                    with open(full_blacklist_path, "r") as f:
                        data = yaml.safe_load(f)
                        if data and isinstance(data, dict) and "blacklist" in data:
                            blacklist = set(data["blacklist"])
                except Exception:
                    # Treat missing/invalid files as "no blacklist"
                    pass

        results = []
        for mod_name in modules:
            try:
                module = importlib.import_module(mod_name)
            except ImportError:
                continue

            for name in dir(module):
                if name.startswith("_"):
                    continue

                if name in blacklist:
                    continue

                obj = getattr(module, name)
                if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
                    continue

                if self._is_deprecated(obj):
                    continue

                include_patterns = (
                    module_config.get("include_patterns") or module_config.get("include") or ["*"]
                )
                if "*" not in include_patterns and name not in include_patterns:
                    continue

                # Introspect
                io_pattern = self.determine_io_pattern(mod_name, name)
                meta = self.introspector.introspect(
                    func=obj,
                    source_adapter="scipy_ndimage",
                    io_pattern=io_pattern,
                )
                meta.module = mod_name
                meta.qualified_name = f"{mod_name}.{name}"
                meta.fn_id = f"{mod_name}.{name}"
                results.append(meta)
        return results

    def _is_deprecated(self, obj: Any) -> bool:
        """Check if an object is marked as deprecated in its docstring."""
        doc = inspect.getdoc(obj)
        if not doc:
            return False
        doc_clean = doc.strip()
        if doc_clean.startswith("Deprecated") or doc_clean.startswith("DEPRECATED"):
            return True
        if ".. deprecated::" in doc:
            return True
        return False

    def determine_io_pattern(self, module_name: str, func_name: str) -> IOPattern:
        """Determine I/O pattern based on module and function name."""
        # scipy.ndimage functions are predominantly image-to-image transformations
        # (filters, morphology, interpolation, etc.)
        return IOPattern.IMAGE_TO_IMAGE

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern based on function name (legacy/protocol)."""
        # Best effort without module context
        return self.determine_io_pattern("", func_name)

    def _normalize_inputs(self, inputs: list[Artifact]) -> list[Artifact]:
        normalized: list[Artifact] = []
        for item in inputs:
            if isinstance(item, tuple) and len(item) == 2:
                _name, artifact = item
                normalized.append(artifact)
            else:
                normalized.append(item)
        return normalized

    def _load_image(self, artifact: Artifact | dict[str, Any]) -> np.ndarray:
        """Load image data from artifact reference."""
        # Handle both dict and Pydantic model
        if isinstance(artifact, dict):
            uri = artifact.get("uri")
            path = artifact.get("path")
        else:
            uri = getattr(artifact, "uri", None)
            path = getattr(artifact, "path", None)

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
            if parsed.scheme != "file":
                raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

            # Remove leading slash on Windows if path starts with drive letter
            path = unquote(parsed.path)
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
        else:
            # Only path is present
            path = str(Path(path).absolute())

        from bioio import BioImage

        img = BioImage(path)
        # Ensure native TCZYX 5D shape - DO NOT use np.squeeze
        data = img.reader.data
        if hasattr(data, "compute"):
            data = data.compute()
        return data

    def _save_image(
        self,
        array: np.ndarray | np.number | float | int,
        work_dir: Path | None = None,
        axes: str | None = None,
        metadata_override: dict[str, Any] | None = None,
    ) -> dict:
        """Save image array to file and return artifact reference dict."""
        # Handle scalar outputs
        if np.isscalar(array):
            array = np.array([array])

        # Ensure at least 2D for tifffile/OME-TIFF compatibility if it's 1D
        if array.ndim == 1:
            array = array[np.newaxis, :]  # Convert to (1, N)
            if axes == "X":
                axes = "YX"
            elif not axes:
                axes = "YX"

        # Use .ome.tiff extension for better compatibility
        ext = ".ome.tiff"

        # Dtype safety: If the output dtype is int64, cast to int32/uint32 for OME-TIFF compatibility
        if array.dtype == np.int64:
            array = array.astype(np.int32)
        elif array.dtype == np.uint64:
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
        except Exception as e:
            logger.warning(f"Failed to save via OmeTiffWriter: {e}")

        if not saved:
            if tifffile is None:
                raise RuntimeError("tifffile is required for saving images")
            metadata = {"axes": inferred_axes} if inferred_axes else None
            tifffile.imwrite(path, array, metadata=metadata, photometric="minisblack")

        # Return artifact reference as dict
        meta = {
            "axes": inferred_axes,
            "dims": list(inferred_axes) if inferred_axes else [],
            "ndim": array.ndim,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
        }
        # Pass through physical resolution and channel names if present
        if metadata_override:
            if "physical_pixel_sizes" in metadata_override:
                meta["physical_pixel_sizes"] = metadata_override["physical_pixel_sizes"]
            if "channel_names" in metadata_override:
                meta["channel_names"] = metadata_override["channel_names"]

        ref = {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "uri": path.absolute().as_uri(),
            "path": str(path.absolute()),
            "metadata": meta,
        }
        return ref

    def _extract_axes(self, artifact: Artifact | dict[str, Any]) -> str:
        metadata: dict[str, Any] = {}
        if isinstance(artifact, dict):
            metadata = artifact.get("metadata") or {}
        else:
            metadata = getattr(artifact, "metadata", {}) or {}
        return str(metadata.get("axes") or "")

    def _infer_axes(self, array: np.ndarray) -> str:
        axes_map = {
            1: "X",
            2: "YX",
            3: "ZYX",
            4: "CZYX",
            5: "TCZYX",
        }
        return axes_map.get(array.ndim, "")

    def _save_scalar(self, value: Any, work_dir: Path | None = None) -> dict:
        """Save scalar value to JSON and return artifact reference dict."""
        import json

        if work_dir is None:
            # Use system temp directory
            fd, path_str = tempfile.mkstemp(suffix=".json")
            import os

            os.close(fd)
            path = Path(path_str)
        else:
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / "output.json"

        # Convert numpy scalars to native python types
        if hasattr(value, "item"):
            val_to_save = value.item()
        else:
            val_to_save = value

        with open(path, "w") as f:
            json.dump({"value": val_to_save}, f)

        return {
            "type": "NativeOutputRef",
            "format": "json",
            "uri": path.absolute().as_uri(),
            "path": str(path.absolute()),
            "metadata": {"dtype": str(type(val_to_save).__name__)},
        }

    def execute(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute the scipy.ndimage function with metadata preservation and dtype safety."""
        # 1) Named input resolution
        # Find primary image input by key preference: 'image' then 'input' then first artifact-like entry
        input_dict = dict(inputs)
        primary_key = None
        if "image" in input_dict:
            primary_key = "image"
        elif "input" in input_dict:
            primary_key = "input"
        else:
            # Find first entry that looks like an artifact
            for name, val in inputs:
                if isinstance(val, dict) and any(
                    k in val for k in ("ref_id", "uri", "path", "type")
                ):
                    primary_key = name
                    break

        primary_artifact = input_dict.get(primary_key) if primary_key else None

        # 2) Force new artifact (no in-place)
        params.pop("output", None)

        # 3) Callable parameters
        # For known callable parameter names (start with: function, callback), resolve if string
        for key, val in list(params.items()):
            if (key.startswith("function") or key.startswith("callback")) and isinstance(val, str):
                params[key] = resolve_callable(val)

        # 4) Auxiliary array artifacts
        # For any additional artifact-like inputs whose names match a missing param key
        for name, val in inputs:
            if name == primary_key:
                continue
            # If it's an artifact reference and not already in params
            if isinstance(val, dict) and any(k in val for k in ("ref_id", "uri", "path", "type")):
                if name not in params:
                    params[name] = self._load_image(val)

        # Also support params containing artifact-like dicts or obj:// URIs for array params
        for key, val in list(params.items()):
            if isinstance(val, dict) and any(k in val for k in ("ref_id", "uri", "path", "type")):
                params[key] = self._load_image(val)
            elif isinstance(val, str) and val.startswith("obj://"):
                params[key] = self._load_image({"uri": val})

        # Load primary image and preserve metadata
        image_data = None
        metadata_override = {}
        axes = ""
        if primary_artifact:
            image_data = self._load_image(primary_artifact)
            axes = self._extract_axes(primary_artifact)

            # Extract pass-through metadata
            meta = (
                primary_artifact.get("metadata", {})
                if isinstance(primary_artifact, dict)
                else getattr(primary_artifact, "metadata", {})
            )
            if meta:
                if "physical_pixel_sizes" in meta:
                    metadata_override["physical_pixel_sizes"] = meta["physical_pixel_sizes"]
                if "channel_names" in meta:
                    metadata_override["channel_names"] = meta["channel_names"]

        # 5) Memory safety / dtype
        # If the primary input dtype is uint16 and the array is "large", cast to float32
        # Threshold: 16 MB
        if image_data is not None and image_data.dtype == np.uint16:
            if image_data.nbytes >= 16 * 1024 * 1024:
                logger.info(f"Casting large uint16 input ({image_data.nbytes} bytes) to float32")
                image_data = image_data.astype(np.float32)

        # Resolve function
        parts = fn_id.split(".")
        if len(parts) < 3:
            raise ValueError(f"Invalid fn_id: {fn_id}")

        module_path = ".".join(parts[:-1])
        func_name = parts[-1]

        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # Execute
        if image_data is not None:
            # Scipy ndimage functions take the input array as the first positional argument
            result = func(image_data, **params)
        else:
            result = func(**params)

        # 6) Output metadata override
        # Returns a list containing the output artifact reference dict
        # Check if result is an image array or a scalar/measurements
        if isinstance(result, np.ndarray) and result.ndim > 0:
            output_ref = self._save_image(
                result, work_dir=work_dir, axes=axes, metadata_override=metadata_override
            )
        else:
            # Scalar or small array result (measurements)
            output_ref = self._save_scalar(result, work_dir=work_dir)

        return [output_ref]

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        return None
