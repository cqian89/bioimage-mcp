"""
PhasorPy adapter for dynamic function registry.

Provides integration with phasorpy library for FLIM phasor analysis.
"""

import importlib
import inspect
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np

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

    def _load_image(self, artifact: Artifact) -> np.ndarray:
        """Load image data from artifact reference."""
        if isinstance(artifact, dict):
            uri = artifact.get("uri", "")
            fmt = artifact.get("format")
        else:
            uri = getattr(artifact, "uri", "")
            fmt = getattr(artifact, "format", None)

        if not uri:
            raise ValueError(f"Artifact missing URI: {artifact}")

        # Parse URI and get file path
        parsed = urlparse(uri)
        path = parsed.path
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]

        from bioio import BioImage

        img = BioImage(path)
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
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[Artifact]:
        """Execute a phasorpy function.

        Args:
            fn_id: Function ID like "phasorpy.phasor_from_signal"
            inputs: Input artifacts (BioImageRef)
            params: Parameters for the function
            work_dir: Optional working directory for execution

        Returns:
            List of output artifacts
        """
        # Extract function name from fn_id
        func_name = fn_id.split(".")[-1]

        # Get the actual function
        if func_name == "phasor_from_signal":
            target_fn = phasor_from_signal
        elif func_name == "phasor_transform":
            target_fn = phasor_transform
        else:
            raise ValueError(f"Unknown function: {func_name}")

        if target_fn is None:
            raise RuntimeError(f"phasorpy is not installed, cannot execute {func_name}")

        # Resolve inputs
        args = []
        kwargs = dict(params)

        # Map inputs to function parameters
        # For phasor_from_signal: takes 'signal'
        # For phasor_transform: takes 'real', 'imag', 'real_zero', 'imag_zero', etc.
        input_map = (
            dict(inputs)
            if isinstance(inputs, list) and inputs and isinstance(inputs[0], tuple)
            else {}
        )
        if not input_map and inputs:
            # Fallback for simple list of artifacts
            if func_name == "phasor_from_signal":
                input_map = {"signal": inputs[0]}
            elif func_name == "phasor_transform" and len(inputs) >= 2:
                input_map = {"real": inputs[0], "imag": inputs[1]}
                if len(inputs) >= 4:
                    input_map["real_zero"] = inputs[2]
                    input_map["imag_zero"] = inputs[3]

        # Load and set image data in kwargs
        for name, artifact in input_map.items():
            kwargs[name] = self._load_image(artifact)

        # Execute
        if func_name == "phasor_from_signal":
            # phasor_from_signal(signal, /, ...)
            signal_data = kwargs.pop("signal", None)
            if signal_data is None:
                raise ValueError("Missing 'signal' input for phasor_from_signal")
            result = target_fn(signal_data, **kwargs)
        else:
            result = target_fn(**kwargs)

        # Handle outputs
        outputs = []
        if func_name == "phasor_from_signal":
            # returns (mean, real, imag)
            mean, real, imag = result
            outputs.append(self._save_image(mean, work_dir, "phasor-mean", "TCZYX"))
            outputs.append(self._save_image(real, work_dir, "phasor-real", "TCZYX"))
            outputs.append(self._save_image(imag, work_dir, "phasor-imag", "TCZYX"))
        elif func_name == "phasor_transform":
            # returns (real, imag)
            real, imag = result
            outputs.append(self._save_image(real, work_dir, "phasor-real", "TCZYX"))
            outputs.append(self._save_image(imag, work_dir, "phasor-imag", "TCZYX"))

        return outputs
