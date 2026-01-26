from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.adapters.scipy_signal import ScipySignalAdapter
from bioimage_mcp.registry.dynamic.adapters.scipy_spatial import ScipySpatialAdapter
from bioimage_mcp.registry.dynamic.adapters.scipy_stats import ScipyStatsAdapter

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement
    from bioimage_mcp.artifacts.base import Artifact
    from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

logger = logging.getLogger(__name__)


class ScipyAdapter(BaseAdapter):
    """Composite adapter for Scipy submodules (ndimage, fft, stats)."""

    def __init__(self) -> None:
        self.ndimage = ScipyNdimageAdapter()
        self.stats = ScipyStatsAdapter()
        self.spatial = ScipySpatialAdapter()
        self.signal = ScipySignalAdapter()

    def _get_adapter(self, module_name: str) -> BaseAdapter:
        """Route to the appropriate sub-adapter based on module name."""
        if module_name.startswith("scipy.stats"):
            return self.stats
        if module_name.startswith("scipy.spatial"):
            return self.spatial
        if module_name.startswith("scipy.signal"):
            return self.signal
        # Default to ndimage (also handles fft via generic array processing)
        return self.ndimage

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions across multiple Scipy submodules."""
        results = []
        modules = module_config.get("modules", [])
        if not modules:
            # Fallback to single module_name if provided
            mod_name = module_config.get("module_name")
            modules = [mod_name] if mod_name else []

        for mod in modules:
            sub_config = module_config.copy()
            sub_config["modules"] = [mod]
            # Ensure _manifest_path is preserved for blacklist resolution
            if "_manifest_path" in module_config:
                sub_config["_manifest_path"] = module_config["_manifest_path"]

            adapter = self._get_adapter(mod)
            results.extend(adapter.discover(sub_config))
        return results

    def execute(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Any | None = None,
    ) -> list[dict]:
        """Route execution to the appropriate sub-adapter."""
        # Strip optional tool prefix (e.g. base.scipy.stats.ttest_ind -> scipy.stats.ttest_ind)
        parts = fn_id.split(".")
        if "scipy" in parts:
            idx = parts.index("scipy")
            parts = parts[idx:]

        clean_fn_id = ".".join(parts)

        # Infer module from fn_id (e.g. scipy.stats.ttest_ind -> scipy.stats)
        if len(parts) >= 3:
            module_name = ".".join(parts[:-1])
            # Handle distribution methods like scipy.stats.norm.pdf -> scipy.stats
            if module_name.startswith("scipy.stats"):
                module_name = "scipy.stats"
        else:
            module_name = ""

        adapter = self._get_adapter(module_name)
        return adapter.execute(clean_fn_id, inputs, params, work_dir=work_dir)

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern (defaulting to ndimage logic)."""
        return self.ndimage.resolve_io_pattern(func_name, signature)

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints from the appropriate sub-adapter."""
        adapter = self._get_adapter(module_name)
        return adapter.generate_dimension_hints(module_name, func_name)
