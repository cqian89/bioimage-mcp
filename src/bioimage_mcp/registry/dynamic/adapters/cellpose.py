"""
Cellpose adapter for dynamic function registry.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

# Import cellpose functions at module level for patching in tests
try:
    from cellpose.models import CellposeModel
except ImportError:
    CellposeModel = None

try:
    import cellpose.train
except ImportError:
    cellpose_train = None
else:
    cellpose_train = cellpose.train


class CellposeAdapter:
    """Adapter for cellpose library functions."""

    # Functions to expose
    DISCOVERABLE_FUNCTIONS = {
        "cellpose.models.CellposeModel": ["eval"],
        "cellpose.train": ["train_seg"],
    }

    # Model types for segment
    MODEL_TYPES = ["cyto3", "cyto2", "cyto", "nuclei", "tissuenet", "livecell"]

    def __init__(self):
        """Initialize CellposeAdapter."""
        self.introspector = Introspector()

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover cellpose functions.

        Args:
            module_config: Configuration from manifest with:
                - module_name: module name to scan (e.g., "cellpose.models.CellposeModel")
                - modules: alternative list of module names
        """
        module_name = module_config.get("module_name", "")
        modules = module_config.get("modules", [])

        target_modules = modules + ([module_name] if module_name else [])

        # Mapping for backward compatibility in module names
        module_mapping = {"cellpose.models": "cellpose.models.CellposeModel"}
        target_modules = [module_mapping.get(t, t) for t in target_modules]

        all_metadata = []

        for target in target_modules:
            if target in self.DISCOVERABLE_FUNCTIONS:
                funcs_to_discover = self.DISCOVERABLE_FUNCTIONS[target]

                # Special handling for CellposeModel (class methods)
                if target == "cellpose.models.CellposeModel":
                    if CellposeModel is None:
                        continue

                    for func_name in funcs_to_discover:
                        if hasattr(CellposeModel, func_name):
                            func = getattr(CellposeModel, func_name)
                            # Primary discovery (cellpose.eval)
                            meta = self._introspect_and_format(
                                func, "cellpose.models", f"cellpose.{func_name}", func_name
                            )
                            all_metadata.append(meta)

                # Handling for modules
                elif target == "cellpose.train":
                    if cellpose_train is None:
                        continue

                    for func_name in funcs_to_discover:
                        if hasattr(cellpose_train, func_name):
                            func = getattr(cellpose_train, func_name)
                            meta = self._introspect_and_format(
                                func, "cellpose.train", f"cellpose.{func_name}", func_name
                            )
                            all_metadata.append(meta)

        return all_metadata

    def _introspect_and_format(
        self, func: Any, module: str, fn_id: str, display_name: str
    ) -> FunctionMetadata:
        """Helper to introspect and format metadata."""
        io_pattern = self.resolve_io_pattern(display_name, None)
        metadata = self.introspector.introspect(
            func=func,
            source_adapter="cellpose",
            io_pattern=io_pattern,
        )
        metadata.name = display_name
        metadata.module = module
        metadata.fn_id = fn_id
        metadata.qualified_name = f"{module}.{display_name}"

        # Clean up parameters
        if "self" in metadata.parameters:
            del metadata.parameters["self"]

        # Add model_type as a parameter for segmentation functions if not present
        if display_name in ["eval", "segment"] and "model_type" not in metadata.parameters:
            from bioimage_mcp.registry.dynamic.models import ParameterSchema

            metadata.parameters["model_type"] = ParameterSchema(
                name="model_type",
                type="string",
                description=f"Cellpose model type. One of: {', '.join(self.MODEL_TYPES)}",
                default="cyto3",
                required=False,
            )

        return metadata

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern from function name.

        Args:
            func_name: Name of the function
            signature: Function signature (unused)

        Returns:
            Categorized I/O pattern
        """
        if func_name in ["segment", "eval"]:
            return IOPattern.IMAGE_TO_LABELS
        if func_name == "train_seg":
            return IOPattern.TRAINING
        return IOPattern.GENERIC

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact] | list[tuple[str, Artifact]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[Artifact]:
        """Execute cellpose function by reusing existing ops.

        Args:
            fn_id: Unique function identifier
            inputs: List of input artifacts or (name, artifact) tuples
            params: Parameter dictionary
            work_dir: Optional working directory for execution

        Returns:
            List of output artifacts
        """
        if fn_id not in ["cellpose.segment", "cellpose.eval"]:
            raise NotImplementedError(
                f"Execution for {fn_id} is not yet implemented in CellposeAdapter."
            )

        # Ensure we can import run_segment from the cellpose tool pack
        try:
            from bioimage_mcp_cellpose.ops.segment import run_segment
        except ImportError:
            # Fallback: try to find it in tools/cellpose/bioimage_mcp_cellpose/ops
            import sys

            root = Path(__file__).parents[5]
            tools_path = root / "tools" / "cellpose"
            if tools_path.exists() and str(tools_path) not in sys.path:
                sys.path.append(str(tools_path))

            try:
                from bioimage_mcp_cellpose.ops.segment import run_segment
            except ImportError:
                raise RuntimeError(
                    "Could not import run_segment from cellpose tool pack. "
                    "Ensure it is in PYTHONPATH."
                ) from None

        # Convert inputs list to dict expected by run_segment
        input_dict = {}
        if isinstance(inputs, list) and inputs:
            if isinstance(inputs[0], tuple):
                # Handle list of (name, artifact) tuples
                for name, artifact in inputs:
                    input_dict[name] = (
                        artifact.model_dump() if hasattr(artifact, "model_dump") else artifact
                    )
            else:
                # Fallback for simple list of artifacts - assume first is 'image'
                artifact = inputs[0]
                input_dict["image"] = (
                    artifact.model_dump() if hasattr(artifact, "model_dump") else artifact
                )

        # Ensure work_dir is a Path and exists
        if work_dir is None:
            work_dir_path = Path(tempfile.mkdtemp())
        else:
            work_dir_path = Path(work_dir)
            work_dir_path.mkdir(parents=True, exist_ok=True)

        # Execute run_segment
        # run_segment returns a dict like {'labels': {...}, 'cellpose_bundle': {...}}
        result_dict = run_segment(input_dict, params, work_dir_path)

        # Convert result dict back to list of Artifact (ArtifactRef)
        outputs = []

        for key in ["labels", "cellpose_bundle"]:
            if key in result_dict:
                val = result_dict[key]
                if isinstance(val, dict):
                    # In v0.1, result_dict values are dicts that look like ArtifactRef
                    # but may missing some fields like ref_id, mime_type, created_at
                    # since run_segment creates them directly.
                    # We might need to wrap them in ArtifactRef if needed,
                    # but for now we return them as is if they are already refs.
                    outputs.append(val)

        return outputs

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance.

        Args:
            module_name: Name of the module
            func_name: Name of the function

        Returns:
            DimensionRequirement or None
        """
        from bioimage_mcp.api.schemas import DimensionRequirement

        if func_name in ["segment", "eval"]:
            return DimensionRequirement(
                min_ndim=2,
                max_ndim=3,
                expected_axes=["Y", "X"],
                squeeze_singleton=True,
                preprocessing_instructions=[
                    "Squeeze singleton T and C dimensions first",
                    "Cellpose expects 2D (YX), 3D (ZYX), or 4D (CZYX) input",
                    "Use base.xarray.squeeze for preprocessing",
                ],
            )
        return None
