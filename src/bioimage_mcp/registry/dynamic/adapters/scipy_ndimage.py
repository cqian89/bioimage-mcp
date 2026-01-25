"""
Adapter for scipy.ndimage functions.
"""

from __future__ import annotations

import importlib
import inspect
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from urllib.parse import unquote, urlparse

import numpy as np

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

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

    def _load_image(self, artifact: Artifact) -> np.ndarray:
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
        data = img.reader.data
        if hasattr(data, "compute"):
            data = data.compute()
        return data

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

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute the function."""
        # fn_id = scipy.ndimage.gaussian_filter
        parts = fn_id.split(".")
        if len(parts) < 3:
            raise ValueError(f"Invalid fn_id: {fn_id}")

        module_path = ".".join(parts[:-1])
        func_name = parts[-1]

        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # Load input images
        args = []
        normalized_inputs = self._normalize_inputs(inputs)
        # Filter out metadata entries
        normalized_inputs = [
            art
            for art in normalized_inputs
            if not (isinstance(art, str) and (" " in art or len(art) > 64))
        ]
        axes = ""
        if normalized_inputs:
            # Load the first input as numpy array
            image_data = self._load_image(normalized_inputs[0])
            args.append(image_data)
            axes = self._extract_axes(normalized_inputs[0])

        # Execute function
        result = func(*args, **params)

        # Save result and create artifact reference dict
        output_ref = self._save_image(result, work_dir=work_dir, axes=axes)

        return [output_ref]

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        return None
