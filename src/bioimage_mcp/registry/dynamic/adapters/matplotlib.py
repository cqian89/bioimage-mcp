from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema
from bioimage_mcp.registry.dynamic.adapters.matplotlib_allowlists import (
    MATPLOTLIB_DENYLIST,
    MATPLOTLIB_PYPLOT_ALLOWLIST,
    MATPLOTLIB_FIGURE_ALLOWLIST,
    MATPLOTLIB_AXES_ALLOWLIST,
    MATPLOTLIB_PATCHES_ALLOWLIST,
)

if TYPE_CHECKING:
    from bioimage_mcp.artifacts.base import Artifact
    from bioimage_mcp.api.schemas import DimensionRequirement


class MatplotlibAdapter(BaseAdapter):
    """Adapter for Matplotlib that satisfies the BaseAdapter protocol."""

    def __init__(self) -> None:
        """Initialize the adapter and enforce the Agg backend."""
        try:
            import matplotlib

            matplotlib.use("Agg")
        except ImportError:
            # Matplotlib might not be available in the core server environment
            # during discovery, which is fine as long as we don't call it.
            pass

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover matplotlib functions from the allowlists."""
        discovery: list[FunctionMetadata] = []

        # Modules requested in config
        requested_modules = module_config.get("modules", [])

        allowlists = [
            (
                "matplotlib.pyplot",
                "matplotlib.pyplot",
                "base.matplotlib.pyplot",
                MATPLOTLIB_PYPLOT_ALLOWLIST,
            ),
            (
                "matplotlib.figure",
                "matplotlib.figure.Figure",
                "base.matplotlib.Figure",
                MATPLOTLIB_FIGURE_ALLOWLIST,
            ),
            (
                "matplotlib.axes",
                "matplotlib.axes.Axes",
                "base.matplotlib.Axes",
                MATPLOTLIB_AXES_ALLOWLIST,
            ),
            (
                "matplotlib.patches",
                "matplotlib.patches",
                "base.matplotlib.patches",
                MATPLOTLIB_PATCHES_ALLOWLIST,
            ),
        ]

        for mod_name, qual_prefix, id_prefix, allowlist in allowlists:
            if not requested_modules or mod_name in requested_modules:
                for name, info in allowlist.items():
                    # Parse parameters
                    params = {}
                    if "params" in info:
                        for p_name, p_info in info["params"].items():
                            params[p_name] = ParameterSchema(
                                name=p_name,
                                type=p_info.get("type", "string"),
                                description=p_info.get("description", ""),
                                default=p_info.get("default"),
                                required=p_info.get("required", False),
                                items=p_info.get("items"),
                            )

                    # Map io_pattern
                    io_pattern_str = info.get("io_pattern", "IMAGE_TO_IMAGE")
                    try:
                        io_pattern = IOPattern[io_pattern_str]
                    except KeyError:
                        io_pattern = IOPattern.IMAGE_TO_IMAGE

                    discovery.append(
                        FunctionMetadata(
                            name=name,
                            module=mod_name,
                            qualified_name=f"{qual_prefix}.{name}",
                            fn_id=f"{id_prefix}.{name}",
                            source_adapter="matplotlib",
                            description=info.get("summary", ""),
                            parameters=params,
                            tags=["visualization", "matplotlib"],
                            io_pattern=io_pattern,
                        )
                    )

        return discovery

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Any = None,
    ) -> list[dict]:
        """Execute a matplotlib function.

        Dispatches to implementation in bioimage_mcp_base.ops.matplotlib_ops.
        """
        # Safety check: Block interactive methods

        method_name = fn_id.split(".")[-1]
        if method_name in MATPLOTLIB_DENYLIST:
            raise ValueError(f"Function {fn_id} is blocked for safety (interactive GUI method).")

        # Check if it's in any allowlist
        is_allowed = (
            method_name in MATPLOTLIB_PYPLOT_ALLOWLIST
            or method_name in MATPLOTLIB_FIGURE_ALLOWLIST
            or method_name in MATPLOTLIB_AXES_ALLOWLIST
            or method_name in MATPLOTLIB_PATCHES_ALLOWLIST
        )

        if not is_allowed:
            raise ValueError(f"Function {fn_id} is unknown or not allowed.")

        # Deferred import to avoid heavy dependencies in core server
        from bioimage_mcp_base.ops import matplotlib_ops

        # Normalize inputs for dispatch
        normalized_inputs = self._normalize_inputs(inputs)

        if fn_id.endswith("matplotlib.pyplot.subplots"):
            return matplotlib_ops.subplots(**params)
        if fn_id.endswith("matplotlib.pyplot.figure"):
            return matplotlib_ops.figure(**params)
        if fn_id.endswith("matplotlib.Axes.hist"):
            return matplotlib_ops.hist(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.boxplot"):
            return matplotlib_ops.boxplot(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.violinplot"):
            return matplotlib_ops.violinplot(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.plot"):
            return matplotlib_ops.plot(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.scatter"):
            return matplotlib_ops.scatter(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.imshow"):
            return matplotlib_ops.imshow(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.add_patch"):
            return matplotlib_ops.add_patch(normalized_inputs, params)
        if fn_id.endswith("matplotlib.Axes.set_xlabel"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "set_xlabel")
        if fn_id.endswith("matplotlib.Axes.set_ylabel"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "set_ylabel")
        if fn_id.endswith("matplotlib.Axes.set_title"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "set_title")
        if fn_id.endswith("matplotlib.Axes.set_xlim"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "set_xlim")
        if fn_id.endswith("matplotlib.Axes.set_ylim"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "set_ylim")
        if fn_id.endswith("matplotlib.Axes.grid"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "grid")
        if fn_id.endswith("matplotlib.patches.Circle"):
            return matplotlib_ops.create_circle(params)
        if fn_id.endswith("matplotlib.patches.Rectangle"):
            return matplotlib_ops.create_rectangle(params)
        if fn_id.endswith("matplotlib.Figure.savefig"):
            return matplotlib_ops.savefig(normalized_inputs, params, work_dir)
        if fn_id.endswith("matplotlib.Figure.tight_layout"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "tight_layout")
        if fn_id.endswith("matplotlib.Figure.suptitle"):
            return matplotlib_ops.generic_op(normalized_inputs, params, "suptitle")

        return []

    def _normalize_inputs(self, inputs: list[Artifact]) -> list[tuple[str, Artifact]]:
        """Normalize inputs to (name, artifact) tuples."""
        normalized: list[tuple[str, Artifact]] = []
        for idx, item in enumerate(inputs):
            if isinstance(item, tuple) and len(item) == 2:
                name, artifact = item
            else:
                # Heuristic for default names if not provided
                if idx == 0:
                    name = "axes" if "Axes" in str(item) else "figure"
                else:
                    name = f"input_{idx}"
                artifact = item
            normalized.append((str(name), artifact))
        return normalized

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern from function signature."""
        return IOPattern.IMAGE_TO_IMAGE

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        return None
