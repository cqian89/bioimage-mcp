from __future__ import annotations

import fnmatch
import hashlib
import logging
import sys
from pathlib import Path
from typing import Any

from bioimage_mcp.bootstrap.env_manager import get_env_paths
from bioimage_mcp.registry.diagnostics import EngineEvent, EngineEventType
from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
from bioimage_mcp.registry.dynamic.meta_list_cache import MetaListCache
from bioimage_mcp.registry.dynamic.models import IOPattern, ParameterSchema
from bioimage_mcp.registry.manifest_schema import Function, FunctionOverlay, Port, ToolManifest
from bioimage_mcp.registry.static.inspector import inspect_module
from bioimage_mcp.registry.static.schema_normalize import normalize_json_schema
from bioimage_mcp.registry.utils import summarize_docstring
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.runtimes.meta_protocol import parse_meta_describe_result, parse_meta_list_result

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root
        self._events: list[EngineEvent] = []

    def discover(self, manifest: ToolManifest) -> tuple[list[Function], list[EngineEvent]]:
        """Unified discovery for a tool manifest.

        Performs AST-first introspection with runtime fallback.
        """
        self._events = []
        functions: list[Function] = []
        existing_fn_ids: set[str] = set()

        # 1. Start with static functions defined in manifest
        for fn in manifest.functions:
            normalized = self._normalize_function(fn, manifest)
            functions.append(normalized)
            existing_fn_ids.add(normalized.fn_id)

        runtime_functions: list[dict[str, Any]] = []
        if manifest.dynamic_sources and any(
            self._should_use_runtime_list(source) for source in manifest.dynamic_sources
        ):
            runtime_functions = self._runtime_list(manifest)

        # 2. Process dynamic sources
        for source in manifest.dynamic_sources:
            try:
                discovered = self._discover_dynamic_source(manifest, source, runtime_functions)
                for fn in discovered:
                    if fn.fn_id not in existing_fn_ids:
                        functions.append(fn)
                        existing_fn_ids.add(fn.fn_id)
            except Exception as e:
                msg = f"Dynamic discovery failed for source {source.prefix}: {e}"
                logger.error(msg)
                self._events.append(
                    EngineEvent(
                        type=EngineEventType.SKIPPED_CALLABLE,
                        message=msg,
                        details={"source_prefix": source.prefix},
                    )
                )

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
                        self._events.append(
                            EngineEvent(
                                type=EngineEventType.OVERLAY_APPLIED,
                                fn_id=target_id,
                                message=f"Applied overlay to {target_id}",
                            )
                        )
                        found = True
                        break

                if not found:
                    msg = f"Overlay target {target_id} not found in tool {manifest.tool_id}"
                    logger.warning(msg)
                    self._events.append(
                        EngineEvent(
                            type=EngineEventType.OVERLAY_CONFLICT,
                            fn_id=target_id,
                            message=msg,
                        )
                    )

        return functions, list(self._events)

    def _normalize_function(self, fn: Function, manifest: ToolManifest) -> Function:
        """Normalize fn_id and metadata for manifest-defined functions."""
        env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
        if (
            env_prefix
            and not fn.fn_id.startswith("meta.")
            and not fn.fn_id.startswith(f"{env_prefix}.")
        ):
            fn.fn_id = f"{env_prefix}.{fn.fn_id}"

        fn.tool_id = manifest.tool_id
        fn.introspection_source = fn.introspection_source or "manifest"

        # Ensure params_schema is normalized
        if fn.params_schema:
            fn.params_schema = normalize_json_schema(fn.params_schema)

        return fn

    def _discover_dynamic_source(
        self,
        manifest: ToolManifest,
        source: Any,
        runtime_functions: list[dict[str, Any]],
    ) -> list[Function]:
        """Discover functions from a single dynamic source using AST-first approach."""
        search_paths = [manifest.manifest_path.parent]
        if self.project_root:
            tools_dir = self.project_root / "tools"
            if tools_dir.exists():
                search_paths.append(tools_dir)

        # Include sys.path to allow griffe to find libraries installed in the current environment
        # (Important for discovery of scipy, skimage, etc. when running doctor/server)
        for p in sys.path:
            if p:
                search_paths.append(Path(p))

        self._append_env_site_packages(search_paths, manifest.env_id)

        adapter = ADAPTER_REGISTRY.get(source.adapter)
        runtime_map = self._build_runtime_function_map(manifest, source, runtime_functions)

        if not source.modules or source.adapter in {"scipy", "trackpy"}:
            return self._map_runtime_functions(manifest, source, runtime_functions, set())

        discovered_functions: list[Function] = []
        failed_modules: list[str] = []

        for module_name in source.modules:
            try:
                report = inspect_module(module_name, search_paths)
                found_any = False
                for sc in report.callables:
                    if not self._should_include(
                        sc.name, source.include_patterns, source.exclude_patterns
                    ):
                        continue

                    fn = self._process_callable(manifest, sc, source, adapter, runtime_map)
                    if fn:
                        discovered_functions.append(fn)
                        found_any = True

                if not found_any:
                    include_patterns = source.include_patterns or ["*"]
                    if "*" in include_patterns:
                        logger.info("AST found no callables in module %s", module_name)
                        failed_modules.append(module_name)

            except Exception as e:
                logger.warning("AST inspection failed for module %s: %s", module_name, e)
                failed_modules.append(module_name)

        # Fallback: If AST discovery failed for any module, try runtime discovery
        # (This is important when libraries use lazy_loader or are in isolated environments)
        if failed_modules and source.modules:
            logger.info("Attempting runtime fallback discovery for source %s", source.prefix)

        discovered_functions = self._map_runtime_functions(
            manifest,
            source,
            runtime_functions,
            {fn.fn_id for fn in discovered_functions},
            discovered_functions,
        )

        return discovered_functions

    def _map_runtime_functions(
        self,
        manifest: ToolManifest,
        source: Any,
        runtime_functions: list[dict[str, Any]],
        existing_ids: set[str],
        discovered_functions: list[Function] | None = None,
    ) -> list[Function]:
        if discovered_functions is None:
            discovered_functions = []

        env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
        source_prefix = f"{env_prefix}.{source.prefix}" if env_prefix else source.prefix

        for fn_data in runtime_functions:
            raw_fn_id = fn_data.get("id") or fn_data.get("fn_id", "")

            final_fn_id = self._normalize_runtime_fn_id(
                raw_fn_id,
                source_prefix,
                source.prefix,
                env_prefix,
            )

            if final_fn_id and final_fn_id not in existing_ids:
                # Basic mapping from runtime dict to Function model
                try:
                    inputs, outputs, io_pattern = self._ports_from_runtime_entry(fn_data)

                    description = summarize_docstring(fn_data.get("summary"))
                    if not description:
                        description = summarize_docstring(fn_data.get("description"))
                    if not description:
                        description = summarize_docstring(fn_data.get("name") or final_fn_id)

                    params_schema = fn_data.get("params_schema")
                    if not params_schema:
                        parameters = fn_data.get("parameters")
                        if isinstance(parameters, dict):
                            param_models: dict[str, ParameterSchema] = {}
                            for name, payload in parameters.items():
                                if not isinstance(payload, dict):
                                    continue
                                try:
                                    if "name" in payload:
                                        param_models[name] = ParameterSchema(**payload)
                                    else:
                                        param_models[name] = ParameterSchema(name=name, **payload)
                                except Exception:
                                    continue
                            params_schema = self.parameters_to_json_schema(param_models)

                    if not params_schema:
                        params_schema = {"type": "object"}

                    port_names = {p.name for p in inputs + outputs}
                    if port_names and isinstance(params_schema, dict):
                        properties = params_schema.get("properties")
                        if isinstance(properties, dict):
                            filtered = {k: v for k, v in properties.items() if k not in port_names}
                            params_schema = {**params_schema, "properties": filtered}
                            if "required" in params_schema:
                                params_schema["required"] = [
                                    r for r in params_schema["required"] if r in filtered
                                ]

                    fn = Function(
                        fn_id=final_fn_id,
                        tool_id=manifest.tool_id,
                        name=fn_data["name"],
                        description=description,
                        tags=fn_data.get("tags", []),
                        inputs=inputs,
                        outputs=outputs,
                        params_schema=params_schema,
                        io_pattern=io_pattern.value if io_pattern else fn_data.get("io_pattern"),
                        module=fn_data.get("module"),
                        introspection_source=f"runtime:{fn_data.get('introspection_source', 'meta.list')}",
                    )
                    discovered_functions.append(fn)
                    existing_ids.add(final_fn_id)
                except Exception as e:
                    logger.debug("Failed to map runtime function %s: %s", raw_fn_id, e)
                    continue

        return discovered_functions

    def _append_env_site_packages(self, search_paths: list[Path], env_id: str | None) -> None:
        if not env_id:
            return
        env_paths = get_env_paths()
        env_path = env_paths.get(env_id)
        if not env_path or not env_path.exists():
            return

        candidates: list[Path] = []
        windows_site = env_path / "Lib" / "site-packages"
        if windows_site.exists():
            candidates.append(windows_site)

        lib_dir = env_path / "lib"
        if lib_dir.exists():
            for python_dir in lib_dir.glob("python*"):
                site_packages = python_dir / "site-packages"
                if site_packages.exists():
                    candidates.append(site_packages)

        for candidate in candidates:
            if candidate not in search_paths:
                search_paths.append(candidate)

    def _runtime_list(self, manifest: ToolManifest) -> list[dict[str, Any]]:
        """Call meta.list on the tool pack to get all functions."""
        # 1. Check for persistent cache
        cache = None
        lockfile_hash = None
        if self.project_root and manifest.env_id:
            lockfile_path = self.project_root / "envs" / f"{manifest.env_id}.lock.yml"
            if lockfile_path.exists():
                try:
                    content = lockfile_path.read_bytes()
                    lockfile_hash = hashlib.sha256(content).hexdigest()[:16]
                    cache_dir = (
                        Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id
                    )
                    cache = MetaListCache(cache_dir)

                    cached_results = cache.get(lockfile_hash, manifest.manifest_checksum)
                    if cached_results is not None:
                        logger.debug("Core meta.list cache hit for %s", manifest.tool_id)
                        return cached_results
                except Exception as e:
                    logger.debug("Failed to check meta.list cache: %s", e)

        # 2. Cache miss or disabled: execute tool
        try:
            # We use meta.list command (legacy format usually handles it)
            request = {
                "command": "execute",
                "id": "meta.list",
                "params": {},
            }
            # execute_tool handles spawning the worker
            # Note: execute_tool returns (result_dict, log_text, exit_code)
            result, _log, code = execute_tool(
                entrypoint=manifest.entrypoint,
                request=request,
                env_id=manifest.env_id,
            )
            if code == 0 and isinstance(result, dict) and result.get("ok"):
                parsed = parse_meta_list_result(result)
                # 3. Write to cache if enabled
                if cache and lockfile_hash:
                    cache.put(lockfile_hash, manifest.manifest_checksum, parsed)
                return parsed
        except Exception as e:
            logger.error("Runtime list failed for %s: %s", manifest.tool_id, e)
        return []

    def _should_use_runtime_list(self, source: Any) -> bool:
        if not source.modules:
            return True
        if source.adapter in {"scipy", "trackpy"}:
            return True
        return source.adapter in ADAPTER_REGISTRY

    def _should_include(self, name: str, include: list[str], exclude: list[str]) -> bool:
        if not any(fnmatch.fnmatch(name, pat) for pat in include):
            return False
        if any(fnmatch.fnmatch(name, pat) for pat in exclude):
            return False
        return True

    def _process_callable(
        self,
        manifest: ToolManifest,
        sc: Any,
        source: Any,
        adapter: Any | None,
        runtime_map: dict[str, dict[str, Any]],
    ) -> Function | None:
        """Convert a static callable to a Function, with runtime fallback if needed."""
        env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
        raw_fn_id = sc.qualified_name or (
            f"{source.prefix}.{sc.name}" if source.prefix else sc.name
        )
        if source.prefix and not raw_fn_id.startswith(f"{source.prefix}."):
            raw_fn_id = f"{source.prefix}.{raw_fn_id}"
        if env_prefix and not raw_fn_id.startswith(f"{env_prefix}."):
            fn_id = f"{env_prefix}.{raw_fn_id}"
        else:
            fn_id = raw_fn_id

        runtime_entry = runtime_map.get(fn_id)

        # Basic AST-derived info
        description = summarize_docstring(sc.docstring)
        if not description and runtime_entry:
            description = summarize_docstring(runtime_entry.get("summary"))
            if not description:
                description = summarize_docstring(runtime_entry.get("description"))
            if not description:
                description = summarize_docstring(runtime_entry.get("name"))
        if not description:
            self._events.append(
                EngineEvent(
                    type=EngineEventType.MISSING_DOCS,
                    fn_id=fn_id,
                    message=f"Function {fn_id} missing docstring",
                )
            )

        params_schema = self._generate_static_params_schema(sc)
        introspection_source = "ast"

        # Prefer runtime meta.list parameter schema when available.
        # Runtime metadata comes from tool-pack dynamic discovery adapters and may include
        # richer information than AST (descriptions, enums, array item schemas, and
        # adapter-specific enrichments like regionprops property lists).
        if runtime_entry:
            runtime_params_schema = runtime_entry.get("params_schema")
            if isinstance(runtime_params_schema, dict) and isinstance(
                runtime_params_schema.get("properties"), dict
            ):
                params_schema = runtime_params_schema
                runtime_source = runtime_entry.get("introspection_source") or "meta.list"
                introspection_source = f"runtime:{runtime_source}"
            else:
                parameters = runtime_entry.get("parameters")
                if isinstance(parameters, dict) and parameters:
                    from bioimage_mcp.registry.dynamic.models import ParameterSchema

                    param_models: dict[str, ParameterSchema] = {}
                    for name, payload in parameters.items():
                        if not isinstance(payload, dict):
                            continue
                        try:
                            if "name" in payload:
                                param_models[name] = ParameterSchema(**payload)
                            else:
                                param_models[name] = ParameterSchema(name=name, **payload)
                        except Exception:
                            continue

                    runtime_params_schema = self.parameters_to_json_schema(param_models)
                    if runtime_params_schema.get("properties"):
                        params_schema = runtime_params_schema
                        runtime_source = runtime_entry.get("introspection_source") or "meta.list"
                        introspection_source = f"runtime:{runtime_source}"

        inputs: list[Port] = []
        outputs: list[Port] = []
        io_pattern: IOPattern | None = None

        if runtime_entry:
            inputs, outputs, io_pattern = self._ports_from_runtime_entry(runtime_entry)

        if not inputs and not outputs:
            if not io_pattern and adapter is not None:
                try:
                    module_name = sc.qualified_name.rsplit(".", 1)[0]
                except Exception:
                    module_name = ""
                try:
                    if source.adapter == "phasorpy":
                        io_pattern = adapter.resolve_io_pattern(sc.name, module_name)
                    else:
                        io_pattern = adapter.resolve_io_pattern(sc.name, None)
                except Exception:
                    io_pattern = None

            if not io_pattern:
                io_pattern = self._guess_io_pattern(sc)

            inputs, outputs = self.map_io_pattern_to_ports(io_pattern)

        io_pattern_value = io_pattern.value if io_pattern else None

        # Filter out port names from parameters (enforce artifact separation)
        # We do this BEFORE deciding to fallback so we know if AST is truly incomplete
        port_names = {p.name for p in inputs} | {p.name for p in outputs}
        # Add common artifact parameter names that should be filtered even if not in ports (T051)
        port_names.update(
            {
                "label_image",
                "intensity_image",
                "input_image",
                "src",
                "source",
                "signal",
                "real",
                "imag",
                "mean",
                "objs",
                "objects",
                "data_objects",
                "arrays",
                "XA",
                "XB",
                "x",
                "cond",
            }
        )
        artifact_types = {
            "BioImageRef",
            "LabelImageRef",
            "TableRef",
            "ScalarRef",
            "LogRef",
            "NativeOutputRef",
            "PlotRef",
        }
        original_param_names = {p.name for p in sc.parameters}

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

        # Only fallback when params were expected but missing after filtering
        artifact_only = bool(original_param_names) and original_param_names.issubset(port_names)
        is_ast_incomplete = not params_schema.get("properties") and not artifact_only

        # Only fallback to runtime describe if AST schema is incomplete
        if is_ast_incomplete:
            runtime_info = self._runtime_describe(manifest, fn_id)
            if runtime_info:
                # Runtime overrides AST
                params_schema = runtime_info.get("params_schema", params_schema)
                introspection_source = (
                    f"runtime:{runtime_info.get('introspection_source', 'meta.describe')}"
                )
                self._events.append(
                    EngineEvent(
                        type=EngineEventType.RUNTIME_FALLBACK,
                        fn_id=fn_id,
                        message=f"Used {introspection_source} fallback for {fn_id}",
                    )
                )
            else:
                # If no AST info and runtime failed, skip
                msg = f"Skipping {fn_id}: AST incomplete and runtime fallback failed"
                logger.warning(msg)
                self._events.append(
                    EngineEvent(
                        type=EngineEventType.SKIPPED_CALLABLE,
                        fn_id=fn_id,
                        message=msg,
                    )
                )
                return None

        # Fill missing parameter descriptions to avoid incomplete schemas
        if "properties" in params_schema:
            for p_name, p_schema in params_schema["properties"].items():
                if not p_schema.get("description"):
                    p_schema["description"] = f"{p_name} parameter"

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
            io_pattern=io_pattern_value,
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
            "id": "meta.describe",
            "command": "execute",
            "params": {"target_fn": fn_id},
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
        module_name = sc.qualified_name.rsplit(".", 1)[0].lower()
        param_names = {p.name.lower() for p in sc.parameters}

        if "plot_phasor" in name:
            return IOPattern.PHASOR_PLOT
        if "phasor" in name or "phasorpy" in module_name:
            if "plot" in name or "phasorpy.plot" in module_name:
                return IOPattern.PLOT
            if "phasor_from_signal" in name or "signal" in param_names:
                return IOPattern.SIGNAL_TO_PHASOR
            if "transform" in name:
                return IOPattern.PHASOR_TRANSFORM
            if "calibrate" in name:
                return IOPattern.PHASOR_CALIBRATE
            if "to_apparent_lifetime" in name or "to_polar" in name:
                return IOPattern.PHASOR_TO_SCALAR
            if "from_lifetime" in name or "from_polar" in name:
                return IOPattern.SCALAR_TO_PHASOR
            return IOPattern.PHASOR_TO_OTHER

        if "segment" in name or "label" in name:
            return IOPattern.IMAGE_TO_LABELS
        if "plot" in name or "plot" in module_name:
            return IOPattern.PLOT
        if "table" in name or "table" in module_name:
            if "table" in param_names:
                return IOPattern.TABLE_TO_TABLE
            return IOPattern.IMAGE_TO_TABLE

        return IOPattern.GENERIC

    def _build_runtime_function_map(
        self,
        manifest: ToolManifest,
        source: Any,
        runtime_functions: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        env_prefix = self._env_prefix_from_tool_id(manifest.tool_id)
        source_prefix = f"{env_prefix}.{source.prefix}" if env_prefix else source.prefix
        runtime_map: dict[str, dict[str, Any]] = {}
        for fn_data in runtime_functions:
            raw_fn_id = fn_data.get("id") or fn_data.get("fn_id", "")
            final_fn_id = self._normalize_runtime_fn_id(
                raw_fn_id,
                source_prefix,
                source.prefix,
                env_prefix,
            )
            if final_fn_id:
                runtime_map[final_fn_id] = fn_data
        return runtime_map

    def _normalize_runtime_fn_id(
        self,
        raw_fn_id: str,
        source_prefix: str,
        raw_source_prefix: str,
        env_prefix: str | None,
    ) -> str | None:
        if not raw_fn_id:
            return None

        if raw_fn_id.startswith(f"{source_prefix}."):
            return raw_fn_id

        if raw_source_prefix and raw_fn_id.startswith(f"{raw_source_prefix}."):
            if env_prefix and not raw_fn_id.startswith(f"{env_prefix}."):
                return f"{env_prefix}.{raw_fn_id}"
            return raw_fn_id

        if raw_source_prefix == "" and env_prefix and raw_fn_id.startswith(f"{env_prefix}."):
            return raw_fn_id

        return None

    def _ports_from_runtime_entry(
        self, fn_data: dict[str, Any]
    ) -> tuple[list[Port], list[Port], IOPattern | None]:
        inputs: list[Port] = []
        outputs: list[Port] = []

        for p in fn_data.get("inputs", []):
            if isinstance(p, dict):
                inputs.append(Port(**p))
            else:
                inputs.append(Port(name=p, artifact_type="BioImageRef"))

        for p in fn_data.get("outputs", []):
            if isinstance(p, dict):
                outputs.append(Port(**p))
            else:
                outputs.append(Port(name=p, artifact_type="BioImageRef"))

        io_pattern: IOPattern | None = None
        raw_pattern = fn_data.get("io_pattern")
        if raw_pattern:
            try:
                io_pattern = IOPattern(raw_pattern)
            except Exception:
                io_pattern = None

        if not inputs and not outputs and io_pattern:
            inputs, outputs = self.map_io_pattern_to_ports(io_pattern)

        return inputs, outputs, io_pattern

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
            inputs = [
                Port(name="image", artifact_type="BioImageRef"),
                Port(name="label_image", artifact_type="BioImageRef", required=False),
            ]
            outputs = [Port(name="labels", artifact_type="LabelImageRef")]
        elif pattern == IOPattern.LABELS_TO_LABELS:
            inputs = [Port(name="image", artifact_type="LabelImageRef")]
            outputs = [Port(name="labels", artifact_type="LabelImageRef")]
        elif pattern == IOPattern.LABELS_TO_TABLE:
            inputs = [
                Port(name="label_image", artifact_type="LabelImageRef"),
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
            outputs = [Port(name="output", artifact_type="ObjectRef")]
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
        elif pattern == IOPattern.PHASOR_TO_LIFETIMES:
            inputs = [
                Port(name="real", artifact_type="BioImageRef"),
                Port(name="imag", artifact_type="BioImageRef"),
            ]
            outputs = [
                Port(name="phase_lifetime", artifact_type="BioImageRef"),
                Port(name="modulation_lifetime", artifact_type="BioImageRef"),
            ]
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
