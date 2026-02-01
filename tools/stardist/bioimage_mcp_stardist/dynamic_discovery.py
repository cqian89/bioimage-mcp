from __future__ import annotations

import importlib
from typing import Any

from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema


class StarDistAdapter:
    """Adapter for StarDist library functions and classes."""

    DISCOVERABLE_TARGETS = {
        "stardist.models.StarDist2D": ["__init__", "from_pretrained", "predict_instances"],
        "stardist.models.StarDist3D": ["__init__", "from_pretrained", "predict_instances"],
    }

    def __init__(self):
        self.introspector = Introspector()

    def discover(self, source_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover StarDist functions and classes."""
        prefix = source_config.get("prefix", "stardist")
        all_metadata = []

        for class_path, methods in self.DISCOVERABLE_TARGETS.items():
            cls = self._resolve_class(class_path)
            if not cls:
                continue

            class_simple_name = class_path.split(".")[-1]

            for method_name in methods:
                if method_name == "__init__":
                    # Constructor: e.g. stardist.StarDist2D
                    display_name = class_simple_name
                    fn_id = f"{prefix}.models.{display_name}"
                    func = cls
                    io_pattern = IOPattern.PURE_CONSTRUCTOR
                elif method_name == "from_pretrained":
                    # Static method: e.g. stardist.StarDist2D.from_pretrained
                    display_name = f"{class_simple_name}.{method_name}"
                    fn_id = f"{prefix}.models.{display_name}"
                    func = getattr(cls, method_name)
                    io_pattern = IOPattern.PURE_CONSTRUCTOR
                else:
                    # Method: e.g. stardist.StarDist2D.predict_instances
                    display_name = f"{class_simple_name}.{method_name}"
                    fn_id = f"{prefix}.models.{display_name}"
                    func = getattr(cls, method_name)
                    if method_name == "predict_instances":
                        io_pattern = IOPattern.IMAGE_TO_LABELS_AND_JSON
                    else:
                        io_pattern = IOPattern.GENERIC

                meta = self.introspector.introspect(
                    func=func,
                    source_adapter="stardist",
                    io_pattern=io_pattern,
                )
                meta.name = display_name
                meta.module = class_path
                meta.fn_id = fn_id
                meta.qualified_name = f"{class_path}.{method_name}"

                # Clean up parameters
                if "self" in meta.parameters:
                    del meta.parameters["self"]

                # If it's a non-static method (not __init__ or from_pretrained),
                # it needs a 'model' ObjectRef input
                if method_name not in ["__init__", "from_pretrained"] and not isinstance(
                    getattr(cls, method_name), staticmethod
                ):
                    meta.parameters["model"] = ParameterSchema(
                        name="model",
                        type="ObjectRef",
                        description=f"Instance of {class_path}",
                        required=True,
                    )

                # Special handling for constructors
                if method_name in ["__init__", "from_pretrained"]:
                    meta.returns = "ObjectRef"
                    meta.tags.append("constructor")
                    meta.tags.append(f"returns:{class_path}")

                # Inject pretrained model names as enum values
                if method_name == "from_pretrained" and "name" in meta.parameters:
                    model_names = self._get_pretrained_model_names(cls)
                    if model_names:
                        meta.parameters["name"].enum = model_names

                all_metadata.append(meta)

        return all_metadata

    def _get_pretrained_model_names(self, cls: Any) -> list[str]:
        """Get available pretrained model names for a StarDist class."""
        try:
            # Import inside to avoid hard dependency in core server
            from csbdeep.models.pretrained import get_registered_models

            models, _ = get_registered_models(cls, return_aliases=True)
            return list(models)
        except (ImportError, Exception):
            return []

    def _resolve_class(self, class_path: str) -> Any:
        try:
            parts = class_path.split(".")
            module_name = ".".join(parts[:-1])
            class_name = parts[-1]
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            return None
