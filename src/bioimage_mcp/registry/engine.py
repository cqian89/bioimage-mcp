from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import Any

from bioimage_mcp.registry.dynamic.models import IOPattern, ParameterSchema
from bioimage_mcp.registry.manifest_schema import Function, FunctionOverlay, Port, ToolManifest
from bioimage_mcp.registry.static.inspector import inspect_module
from bioimage_mcp.registry.static.schema_normalize import normalize_json_schema
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.runtimes.meta_protocol import parse_meta_describe_result

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root

    def discover(self, manifest: ToolManifest) -> tuple[list[Function], list[str]]:
        """Unified discovery for a tool manifest.

        Performs AST-first introspection with runtime fallback.
        """
        functions: list[Function] = []
        existing_fn_ids: set[str] = set()
        warnings: list[str] = []

        # 1. Start with static functions defined in manifest
        for fn in manifest.functions:
            normalized = self._normalize_function(fn, manifest)
            functions.append(normalized)
            existing_fn_ids.add(normalized.fn_id)

        # 2. Process dynamic sources
        for source in manifest.dynamic_sources:
            try:
                discovered = self._discover_dynamic_source(manifest, source)
                for fn in discovered:
                    if fn.fn_id not in existing_fn_ids:
                        functions.append(fn)
                        existing_fn_ids.add(fn.fn_id)
            except Exception as e:
                msg = f"Dynamic discovery failed for source {source.prefix}: {e}"
                logger.error(msg)
                warnings.append(msg)

        # 3. Apply overlays
        if manifest.function_overlays:
            for fn_id, overlay in manifest.function_overlays.items():
                # Overlays use the full fn_id (prefixed)
                env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
                target_id = fn_id
                if env_prefix and not target_id.startswith(f"{env_prefix}."):
                    target_id = f"{env_prefix}.{target_id}"

                found = False
                for i, fn in enumerate(functions):
                    if fn.fn_id == target_id:
                        functions[i] = self.merge_function_overlay(fn, overlay)
                        found = True
                        break

                if not found:
                    msg = f"Overlay target {target_id} not found in tool {manifest.tool_id}"
                    logger.warning(msg)
                    warnings.append(msg)

        return functions, warnings

    def _normalize_function(self, fn: Function, manifest: ToolManifest) -> Function:
        """Normalize fn_id and metadata for manifest-defined functions."""
        env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
        if env_prefix and not fn.fn_id.startswith(f"{env_prefix}."):
            fn.fn_id = f"{env_prefix}.{fn.fn_id}"

        fn.tool_id = manifest.tool_id
        fn.introspection_source = fn.introspection_source or "manifest"

        # Ensure params_schema is normalized
        if fn.params_schema:
            fn.params_schema = normalize_json_schema(fn.params_schema)

        return fn

    def _discover_dynamic_source(self, manifest: ToolManifest, source: Any) -> list[Function]:
        """Discover functions from a single dynamic source using AST-first approach."""
        search_paths = [manifest.manifest_path.parent]
        if self.project_root:
            tools_dir = self.project_root / "tools"
            if tools_dir.exists():
                search_paths.append(tools_dir)

        discovered_functions: list[Function] = []

        for module_name in source.modules:
            try:
                report = inspect_module(module_name, search_paths)
                for sc in report.callables:
                    if not self._should_include(
                        sc.name, source.include_patterns, source.exclude_patterns
                    ):
                        continue

                    fn = self._process_callable(manifest, sc, source.prefix)
                    if fn:
                        discovered_functions.append(fn)
            except Exception as e:
                logger.warning("AST inspection failed for module %s: %s", module_name, e)

        return discovered_functions

    def _should_include(self, name: str, include: list[str], exclude: list[str]) -> bool:
        if not any(fnmatch.fnmatch(name, pat) for pat in include):
            return False
        if any(fnmatch.fnmatch(name, pat) for pat in exclude):
            return False
        return True

    def _process_callable(self, manifest: ToolManifest, sc: Any, prefix: str) -> Function | None:
        """Convert a static callable to a Function, with runtime fallback if needed."""
        env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
        raw_fn_id = f"{prefix}.{sc.name}" if prefix else sc.name
        fn_id = f"{env_prefix}.{raw_fn_id}" if env_prefix else raw_fn_id

        # Basic AST-derived info
        description = sc.docstring or ""
        params_schema = self._generate_static_params_schema(sc)

        introspection_source = "ast"

        # Fallback to runtime describe if AST schema is minimal or we want validation
        runtime_info = self._runtime_describe(manifest, fn_id)
        if runtime_info:
            # Runtime overrides AST
            params_schema = runtime_info.get("params_schema", params_schema)
            introspection_source = (
                f"runtime:{runtime_info.get('introspection_source', 'meta.describe')}"
            )
        elif not params_schema.get("properties"):
            # If no AST info and runtime failed, skip
            logger.warning("Skipping %s: AST incomplete and runtime fallback failed", fn_id)
            return None

        # Fingerprint from source if available
        # fingerprint = callable_fingerprint(sc.source or "") # Not used in Function model yet

        # Heuristic for I/O pattern
        io_pattern = self._guess_io_pattern(sc)
        inputs, outputs = self.map_io_pattern_to_ports(io_pattern)

        # Filter out port names from parameters (enforce artifact separation)
        port_names = {p.name for p in inputs} | {p.name for p in outputs}
        artifact_types = {
            "BioImageRef",
            "LabelImageRef",
            "TableRef",
            "ScalarRef",
            "LogRef",
            "NativeOutputRef",
            "PlotRef",
        }
        if "properties" in params_schema:
            params_schema["properties"] = {
                k: v
                for k, v in params_schema["properties"].items()
                if k not in port_names and v.get("type") not in artifact_types
            }
            if "required" in params_schema:
                params_schema["required"] = [
                    r for r in params_schema["required"] if r in params_schema["properties"]
                ]

        return Function(
            fn_id=fn_id,
            tool_id=manifest.tool_id,
            name=sc.name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            params_schema=normalize_json_schema(params_schema),
            introspection_source=introspection_source,
            module=sc.qualified_name.rsplit(".", 1)[0],
            io_pattern=str(io_pattern.value),
        )

    def _generate_static_params_schema(self, sc: Any) -> dict[str, Any]:
        properties = {}
        required = []
        for p in sc.parameters:
            prop = {"type": self._map_static_type(p.annotation)}
            if p.default is not None:
                prop["default"] = p.default
            else:
                required.append(p.name)
            properties[p.name] = prop

        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    def _map_static_type(self, annotation: str | None) -> str:
        if not annotation:
            return "string"
        a = annotation.lower()
        if "int" in a:
            return "integer"
        if "float" in a or "number" in a:
            return "number"
        if "bool" in a:
            return "boolean"
        if "list" in a or "iterable" in a or "[" in a:
            return "array"
        if "dict" in a or "mapping" in a:
            return "object"
        return "string"

    def _runtime_describe(self, manifest: ToolManifest, fn_id: str) -> dict[str, Any] | None:
        request = {
            "fn_id": "meta.describe",
            "command": "execute",
            "params": {"fn_id": fn_id},
            "inputs": {},
        }
        try:
            response, _, _ = execute_tool(
                entrypoint=manifest.entrypoint,
                request=request,
                env_id=manifest.env_id,
                timeout_seconds=30,
            )
            return parse_meta_describe_result(response)
        except Exception as e:
            logger.debug("Runtime fallback failed for %s: %s", fn_id, e)
            return None

    def _guess_io_pattern(self, sc: Any) -> IOPattern:
        name = sc.name.lower()
        if "segment" in name or "label" in name:
            return IOPattern.IMAGE_TO_LABELS
        return IOPattern.GENERIC

    def _env_prefix_from_tool_id(self, tool_id: str | None) -> str | None:
        if not tool_id:
            return None
        if tool_id.startswith("tools."):
            return tool_id.split(".", 1)[1]
        return tool_id

    @staticmethod
    def map_io_pattern_to_ports(pattern: IOPattern) -> tuple[list[Port], list[Port]]:
        if pattern == IOPattern.IMAGE_TO_IMAGE:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [Port(name="output", artifact_type="BioImageRef")]
        elif pattern == IOPattern.IMAGE_TO_LABELS:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [Port(name="labels", artifact_type="LabelImageRef")]
        elif pattern == IOPattern.LABELS_TO_LABELS:
            inputs = [Port(name="image", artifact_type="LabelImageRef")]
            outputs = [Port(name="labels", artifact_type="LabelImageRef")]
        elif pattern == IOPattern.LABELS_TO_TABLE:
            inputs = [
                Port(name="labels", artifact_type="LabelImageRef"),
                Port(name="intensity_image", artifact_type="BioImageRef", required=False),
            ]
            outputs = [Port(name="table", artifact_type="TableRef")]
        elif pattern == IOPattern.SIGNAL_TO_PHASOR:
            inputs = [Port(name="signal", artifact_type="BioImageRef")]
            outputs = [
                Port(name="mean", artifact_type="BioImageRef"),
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
        elif pattern == IOPattern.PHASOR_TRANSFORM:
            inputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
                Port(name="real_zero", artifact_type="BioImageRef"),
                Port(name="imag_zero", artifact_type="BioImageRef"),
            ]
            outputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
        elif pattern == IOPattern.PHASOR_CALIBRATE:
            inputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
                Port(name="reference_mean", artifact_type="BioImageRef"),
                Port(name="reference_real", artifact_type="BioImageRef"),
                Port(name="reference_imag", artifact_type="BioImageRef"),
            ]
            outputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
        elif pattern == IOPattern.OBJECTREF_CHAIN:
            inputs = [Port(name="image", artifact_type=["BioImageRef", "ObjectRef"])]
            outputs = [Port(name="output", artifact_type="ObjectRef")]
        elif pattern == IOPattern.CONSTRUCTOR:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [Port(name="da", artifact_type="ObjectRef")]
        elif pattern == IOPattern.MULTI_INPUT:
            inputs = [
                Port(name="images", artifact_type=["BioImageRef", "ObjectRef"], is_array=True)
            ]
            outputs = [Port(name="output", artifact_type="BioImageRef")]
        elif pattern == IOPattern.MULTI_TABLE_INPUT:
            inputs = [Port(name="tables", artifact_type=["TableRef", "ObjectRef"], is_array=True)]
            outputs = [Port(name="output", artifact_type="ObjectRef")]
        elif pattern == IOPattern.BINARY:
            inputs = [
                Port(name="image", artifact_type=["BioImageRef", "ObjectRef", "NativeOutputRef"]),
                Port(name="input_1", artifact_type=["BioImageRef", "ObjectRef", "NativeOutputRef"]),
            ]
            outputs = [Port(name="output", artifact_type=["BioImageRef", "ObjectRef"])]
        elif pattern == IOPattern.OBJECT_TO_IMAGE:
            inputs = [Port(name="image", artifact_type=["BioImageRef", "ObjectRef"])]
            outputs = [Port(name="output", artifact_type="BioImageRef")]
        elif pattern == IOPattern.IMAGE_TO_TABLE:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [Port(name="table", artifact_type="TableRef")]
        elif pattern == IOPattern.TABLE_TO_TABLE:
            inputs = [Port(name="table", artifact_type="TableRef")]
            outputs = [Port(name="table", artifact_type="TableRef")]
        elif pattern == IOPattern.PURE_CONSTRUCTOR:
            inputs = []
            outputs = [Port(name="output", artifact_type="ObjectRef")]
        elif pattern == IOPattern.MATPLOTLIB_SUBPLOTS:
            inputs = []
            outputs = [
                Port(name="figure", artifact_type=["FigureRef", "ObjectRef"]),
                Port(name="axes", artifact_type=["AxesRef", "ObjectRef"]),
            ]
        elif pattern == IOPattern.MATPLOTLIB_AXES_OP:
            inputs = [Port(name="axes", artifact_type=["AxesRef", "ObjectRef"])]
            outputs = [Port(name="output", artifact_type="ObjectRef")]
        elif pattern == IOPattern.MATPLOTLIB_FIGURE_OP:
            inputs = [Port(name="figure", artifact_type=["FigureRef", "ObjectRef"])]
            outputs = [Port(name="output", artifact_type="ObjectRef")]
        elif pattern == IOPattern.PLOT:
            inputs = [Port(name="figure", artifact_type="ObjectRef")]
            outputs = [Port(name="plot", artifact_type="PlotRef")]
        elif pattern == IOPattern.PHASOR_PLOT:
            inputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
            outputs = [Port(name="plot", artifact_type="PlotRef")]
        elif pattern == IOPattern.PHASOR_TO_SCALAR:
            inputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
            outputs = [Port(name="output", artifact_type="BioImageRef")]
        elif pattern == IOPattern.SCALAR_TO_PHASOR:
            inputs = []
            outputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
        elif pattern == IOPattern.PHASOR_TO_OTHER:
            inputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
            outputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
        elif pattern == IOPattern.FILE_TO_SIGNAL:
            inputs = []
            outputs = [Port(name="signal", artifact_type="BioImageRef")]
        elif pattern == IOPattern.FILE_TO_REF:
            inputs = []
            outputs = [Port(name="tttr", artifact_type="TTTRRef")]
        elif pattern == IOPattern.REF_TO_JSON:
            inputs = [Port(name="tttr", artifact_type="TTTRRef")]
            outputs = [Port(name="header", artifact_type="ScalarRef")]
        elif pattern == IOPattern.REF_TO_TABLE:
            inputs = [Port(name="tttr", artifact_type="TTTRRef")]
            outputs = [Port(name="table", artifact_type="TableRef")]
        elif pattern == IOPattern.REF_TO_OBJECT:
            inputs = [Port(name="tttr", artifact_type="TTTRRef")]
            outputs = [Port(name="object", artifact_type="ObjectRef")]
        elif pattern == IOPattern.REF_TO_FILE:
            inputs = [Port(name="tttr", artifact_type="TTTRRef")]
            outputs = [Port(name="output", artifact_type="NativeOutputRef")]
        elif pattern == IOPattern.IMAGE_TO_JSON:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.IMAGE_AND_LABELS_TO_JSON:
            inputs = [
                Port(name="image", artifact_type="BioImageRef"),
                Port(name="labels", artifact_type="LabelImageRef", required=False),
            ]
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.IMAGE_TO_LABELS_AND_JSON:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [
                Port(name="labels", artifact_type="LabelImageRef"),
                Port(name="output", artifact_type="ScalarRef"),
            ]
        elif pattern == IOPattern.TABLE_TO_JSON:
            inputs = [Port(name="table", artifact_type="TableRef")]
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.TABLE_PAIR_TO_JSON:
            inputs = [
                Port(name="table_a", artifact_type=["TableRef", "ObjectRef"]),
                Port(name="table_b", artifact_type=["TableRef", "ObjectRef"]),
            ]
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.MULTI_TABLE_TO_JSON:
            inputs = [Port(name="tables", artifact_type=["TableRef", "ObjectRef"], is_array=True)]
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.PARAMS_TO_JSON:
            inputs = []
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.TABLE_TO_OBJECT:
            inputs = [Port(name="table", artifact_type=["TableRef", "ObjectRef"])]
            outputs = [Port(name="object", artifact_type="ObjectRef")]
        elif pattern == IOPattern.OBJECT_AND_TABLE_TO_JSON:
            inputs = [
                Port(name="object", artifact_type="ObjectRef"),
                Port(name="table", artifact_type=["TableRef", "ObjectRef"]),
            ]
            outputs = [Port(name="output", artifact_type="ScalarRef")]
        elif pattern == IOPattern.TABLE_TO_FILE:
            inputs = [Port(name="table", artifact_type=["TableRef", "ObjectRef"])]
            outputs = [Port(name="output", artifact_type="NativeOutputRef")]
        elif pattern == IOPattern.TABLE_PAIR_TO_FILE:
            inputs = [
                Port(name="table_a", artifact_type=["TableRef", "ObjectRef"]),
                Port(name="table_b", artifact_type=["TableRef", "ObjectRef"]),
            ]
            outputs = [Port(name="output", artifact_type="NativeOutputRef")]
        elif pattern == IOPattern.ANY_TO_TABLE:
            inputs = [Port(name="input", artifact_type=["TableRef", "BioImageRef", "ObjectRef"])]
            outputs = [Port(name="table", artifact_type="TableRef")]
        else:
            inputs = [Port(name="image", artifact_type="BioImageRef")]
            outputs = [Port(name="output", artifact_type="BioImageRef")]

        return inputs, outputs

    @staticmethod
    def parameters_to_json_schema(params: dict[str, ParameterSchema]) -> dict:
        if not params:
            return {"type": "object", "properties": {}}

        properties = {}
        required = []

        for param_name, param_schema in params.items():
            prop = {
                "type": param_schema.type,
            }
            if param_schema.description:
                prop["description"] = param_schema.description
            if param_schema.enum is not None:
                prop["enum"] = param_schema.enum
            if param_schema.default is not None:
                prop["default"] = param_schema.default
            if param_schema.additionalProperties is not None:
                prop["additionalProperties"] = param_schema.additionalProperties
            if param_schema.examples is not None:
                prop["examples"] = param_schema.examples
            if param_schema.items is not None:
                prop["items"] = param_schema.items

            properties[param_name] = prop

            if param_schema.required:
                required.append(param_name)

        schema = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema

    @staticmethod
    def deep_merge_dict(base: dict, overlay: dict) -> dict:
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DiscoveryEngine.deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def merge_function_overlay(discovered: Function, overlay: FunctionOverlay) -> Function:
        result = discovered.model_copy(deep=True)

        if overlay.description is not None:
            result.description = overlay.description
        if overlay.tags is not None:
            result.tags = overlay.tags
        if overlay.io_pattern is not None:
            inputs, outputs = DiscoveryEngine.map_io_pattern_to_ports(overlay.io_pattern)
            result.inputs = inputs
            result.outputs = outputs
            result.io_pattern = str(overlay.io_pattern.value)

        if overlay.hints is not None:
            if result.hints is None:
                result.hints = overlay.hints
            else:
                base_hints_dict = result.hints.model_dump(exclude_unset=True)
                overlay_hints_dict = overlay.hints.model_dump(exclude_unset=True)
                merged_hints_dict = DiscoveryEngine.deep_merge_dict(
                    base_hints_dict, overlay_hints_dict
                )
                result.hints = type(result.hints).model_validate(merged_hints_dict)

        if not result.params_schema:
            result.params_schema = {"type": "object", "properties": {}}
        elif "properties" not in result.params_schema:
            result.params_schema["properties"] = {}

        # 1. Handle renames
        if overlay.params_rename:
            for old_name, new_name in overlay.params_rename.items():
                if old_name in result.params_schema["properties"]:
                    result.params_schema["properties"][new_name] = result.params_schema[
                        "properties"
                    ].pop(old_name)
                    if (
                        "required" in result.params_schema
                        and old_name in result.params_schema["required"]
                    ):
                        result.params_schema["required"].remove(old_name)
                        result.params_schema["required"].append(new_name)

        # 2. Handle omissions
        if overlay.params_omit:
            for param_name in overlay.params_omit:
                result.params_schema["properties"].pop(param_name, None)
                if (
                    "required" in result.params_schema
                    and param_name in result.params_schema["required"]
                ):
                    result.params_schema["required"].remove(param_name)

        # 3. Handle overrides
        if overlay.params_override is not None:
            for param_name, overrides in overlay.params_override.items():
                if param_name in result.params_schema["properties"]:
                    result.params_schema["properties"][param_name].update(overrides)
                else:
                    result.params_schema["properties"][param_name] = overrides

        # Final normalization
        result.params_schema = normalize_json_schema(result.params_schema)

        return result
