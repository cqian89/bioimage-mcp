from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Path setup: add src/ to sys.path to access core models
# Assuming we are in tools/trackpy/bioimage_mcp_trackpy/
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern  # noqa: E402
from bioimage_mcp_trackpy.introspect import introspect_module  # noqa: E402


class TrackpyAdapter:
    """Adapter for trackpy dynamic function discovery."""

    def discover(self, config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from trackpy modules.

        Args:
            config: Configuration dictionary containing "modules" list.

        Returns:
            List of FunctionMetadata objects.
        """
        modules = config.get("modules", [])
        results: list[FunctionMetadata] = []

        for module_name in modules:
            discovered = introspect_module(module_name)
            for item in discovered:
                # Convert dict to FunctionMetadata
                # item shape: {"id": ..., "name": ..., "summary": ..., "module": ...,
                #              "io_pattern": ...}

                # Map io_pattern string to IOPattern enum

                io_pattern_str = item.get("io_pattern", "generic")
                try:
                    io_pattern = IOPattern(io_pattern_str)
                except ValueError:
                    io_pattern = IOPattern.GENERIC

                meta = FunctionMetadata(
                    fn_id=item["id"],
                    name=item["name"],
                    module=item["module"],
                    qualified_name=item["id"],
                    source_adapter="trackpy",
                    description=item.get("summary", ""),  # Use summary as initial description
                    io_pattern=io_pattern,
                )
                results.append(meta)

        return results
