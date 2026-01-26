from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from bioimage_mcp.registry.dynamic.adapters.scipy_stats import ScipyStatsAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

logger = logging.getLogger(__name__)


class ScipySpatialAdapter(ScipyStatsAdapter):
    """Adapter for scipy.spatial functions."""

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from configured modules."""
        modules = module_config.get("modules", [])
        if "scipy.spatial" not in modules and "scipy.spatial.distance" not in modules:
            return super().discover(module_config)

        results = []

        # 1. cdist
        results.append(
            FunctionMetadata(
                name="cdist",
                module="scipy.spatial.distance",
                qualified_name="scipy.spatial.distance.cdist",
                fn_id="scipy.spatial.distance.cdist",
                source_adapter="scipy_spatial",
                description="Compute distance between each pair of the two collections of inputs.",
                parameters={
                    "metric": ParameterSchema(
                        name="metric",
                        type="string",
                        enum=["euclidean", "cosine", "mahalanobis"],
                        default="euclidean",
                        required=False,
                    ),
                    "columns_a": ParameterSchema(
                        name="columns_a",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns for table_a",
                        required=False,
                    ),
                    "columns_b": ParameterSchema(
                        name="columns_b",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns for table_b",
                        required=False,
                    ),
                    "vi_strategy": ParameterSchema(
                        name="vi_strategy",
                        type="string",
                        enum=["auto", "from_a", "from_ab", "from_param"],
                        default="auto",
                        required=False,
                    ),
                    "vi": ParameterSchema(
                        name="vi",
                        type="array",
                        items={"type": "array", "items": {"type": "number"}},
                        description="Inverse covariance matrix for mahalanobis when vi_strategy='from_param'",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_PAIR_TO_FILE,
                tags=["spatial", "distance"],
            )
        )

        # 2. Voronoi
        results.append(
            FunctionMetadata(
                name="Voronoi",
                module="scipy.spatial",
                qualified_name="scipy.spatial.Voronoi",
                fn_id="scipy.spatial.Voronoi",
                source_adapter="scipy_spatial",
                description="Compute the Voronoi diagram of a set of points.",
                parameters={
                    "columns": ParameterSchema(
                        name="columns",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_TO_JSON,
                tags=["spatial", "tessellation"],
            )
        )

        # 3. Delaunay
        results.append(
            FunctionMetadata(
                name="Delaunay",
                module="scipy.spatial",
                qualified_name="scipy.spatial.Delaunay",
                fn_id="scipy.spatial.Delaunay",
                source_adapter="scipy_spatial",
                description="Compute the Delaunay triangulation of a set of points.",
                parameters={
                    "columns": ParameterSchema(
                        name="columns",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_TO_JSON,
                tags=["spatial", "tessellation"],
            )
        )

        return results

    def execute(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute spatial functions (stub)."""
        # API execution lands in Plans 09-02/09-03
        raise ValueError(f"Unsupported spatial fn_id: {fn_id}")

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern."""
        if func_name == "cdist":
            return IOPattern.TABLE_PAIR_TO_FILE
        if func_name in ("Voronoi", "Delaunay"):
            return IOPattern.TABLE_TO_JSON
        return IOPattern.GENERIC

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints."""
        return None
