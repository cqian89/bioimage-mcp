"""
Adapter for scipy.ndimage functions.
"""

from __future__ import annotations

import importlib
import inspect
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

try:
    import tifffile
except ImportError:
    tifffile = None


class ScipyNdimageAdapter(BaseAdapter):
    """Adapter for exposing scipy.ndimage functions dynamically."""

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
            # source.model_dump() has "modules": ["scipy.ndimage", ...]
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

            # Filter functions (simple logic for now, respecting include/exclude patterns from config if passed)
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
                    source_adapter="scipy_ndimage",
                    io_pattern=io_pattern,
                )
                meta.module = mod_name
                meta.qualified_name = f"{mod_name}.{name}"
                meta.fn_id = f"{mod_name}.{name}"
                results.append(meta)
        return results

    def determine_io_pattern(self, module_name: str, func_name: str) -> IOPattern:
        """Determine I/O pattern based on module and function name."""
        # scipy.ndimage functions are predominantly image-to-image transformations
        # (filters, morphology, interpolation, etc.)
        return IOPattern.IMAGE_TO_IMAGE

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern based on function name (legacy/protocol)."""
        # Best effort without module context
        return self.determine_io_pattern("", func_name)

    def _load_image(self, artifact: Artifact) -> np.ndarray:
        """Load image data from artifact reference."""
        if tifffile is None:
            raise RuntimeError("tifffile is required for loading images")

        # Handle both dict and Pydantic model
        if isinstance(artifact, dict):
            uri = artifact["uri"]
        else:
            uri = artifact.uri

        # Parse URI and get file path
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

        # Remove leading slash on Windows if path starts with drive letter
        path = parsed.path
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]

        return tifffile.imread(path)

    def _save_image(self, array: np.ndarray, work_dir: Path | None = None) -> dict:
        """Save image array to file and return artifact reference dict."""
        if tifffile is None:
            raise RuntimeError("tifffile is required for saving images")

        # Create temp file
        if work_dir is None:
            # Use system temp directory
            fd, path_str = tempfile.mkstemp(suffix=".tif")
            import os

            os.close(fd)
            path = Path(path_str)
        else:
            # Use provided work directory
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / "output.tif"

        # Save image
        tifffile.imwrite(path, array)

        # Return artifact reference as dict (compatible with entrypoint protocol)
        return {
            "type": "BioImageRef",
            "format": "OME-TIFF",
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
        if inputs:
            # Load the first input as numpy array
            image_data = self._load_image(inputs[0])
            args.append(image_data)

        # Execute function
        result = func(*args, **params)

        # Save result and create artifact reference dict
        output_ref = self._save_image(result, work_dir=work_dir)

        return [output_ref]
