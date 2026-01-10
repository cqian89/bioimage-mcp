from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from bioimage_mcp.registry.diagnostics import ManifestDiagnostic
from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
from bioimage_mcp.registry.dynamic.discovery import discover_functions
from bioimage_mcp.registry.dynamic.models import IOPattern, ParameterSchema
from bioimage_mcp.registry.manifest_schema import Function, FunctionOverlay, Port, ToolManifest


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _map_io_pattern_to_ports(pattern: IOPattern) -> tuple[list[Port], list[Port]]:
    """Map IOPattern to input and output Port lists.

    Args:
        pattern: I/O pattern enum value

    Returns:
        Tuple of (inputs, outputs) as Port lists
    """
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
        # Returns mean, real, imag images
        inputs = [Port(name="signal", artifact_type="BioImageRef")]
        outputs = [
            Port(name="mean", artifact_type="BioImageRef"),
            Port(name="real", artifact_type="BioImageRef"),
            Port(name="imag", artifact_type="BioImageRef"),
        ]
    elif pattern == IOPattern.PHASOR_TRANSFORM:
        # (real, imag) + (real_zero, imag_zero) -> (real, imag)
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
        # phasor_calibrate: (real, imag, ref_mean, ref_real, ref_imag) -> (real, imag)
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
        # Multi-input pattern accepts a list of images or multiple image_N ports
        inputs = [Port(name="image", artifact_type=["BioImageRef", "ObjectRef"])]
        outputs = [Port(name="output", artifact_type="BioImageRef")]
    elif pattern == IOPattern.BINARY:
        inputs = [
            Port(name="image", artifact_type=["BioImageRef", "ObjectRef"]),
            Port(name="input_1", artifact_type=["BioImageRef", "ObjectRef"]),
        ]
        outputs = [Port(name="output", artifact_type=["BioImageRef", "ObjectRef"])]
    elif pattern == IOPattern.OBJECT_TO_IMAGE:
        inputs = [Port(name="image", artifact_type=["BioImageRef", "ObjectRef"])]
        outputs = [Port(name="output", artifact_type="BioImageRef")]
    else:
        # Default/Generic: single input/output
        inputs = [Port(name="image", artifact_type="BioImageRef")]
        outputs = [Port(name="output", artifact_type="BioImageRef")]

    return inputs, outputs


def _parameters_to_json_schema(params: dict[str, ParameterSchema]) -> dict:
    """Convert ParameterSchema dict to JSON Schema.

    Args:
        params: Dictionary of parameter name to ParameterSchema

    Returns:
        JSON Schema object for the parameters
    """
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


def _deep_merge_dict(base: dict, overlay: dict) -> dict:
    """Recursively merge two dictionaries."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def merge_function_overlay(discovered: Function, overlay: FunctionOverlay) -> Function:
    """Deep merge overlay into discovered function.

    Args:
        discovered: The function as discovered from introspection
        overlay: The overlay to apply

    Returns:
        A new Function object with overlay applied
    """
    result = discovered.model_copy(deep=True)

    # Simple override fields
    if overlay.description is not None:
        result.description = overlay.description
    if overlay.tags is not None:
        result.tags = overlay.tags
    if overlay.io_pattern is not None:
        inputs, outputs = _map_io_pattern_to_ports(overlay.io_pattern)
        result.inputs = inputs
        result.outputs = outputs

    # Deep merge hints
    if overlay.hints is not None:
        if result.hints is None:
            result.hints = overlay.hints
        else:
            base_hints_dict = result.hints.model_dump(exclude_unset=True)
            overlay_hints_dict = overlay.hints.model_dump(exclude_unset=True)
            merged_hints_dict = _deep_merge_dict(base_hints_dict, overlay_hints_dict)
            result.hints = type(result.hints).model_validate(merged_hints_dict)

    # Parameter overrides
    if overlay.params_override is not None:
        if not result.params_schema:
            result.params_schema = {"type": "object", "properties": {}}
        elif "properties" not in result.params_schema:
            result.params_schema["properties"] = {}

        for param_name, overrides in overlay.params_override.items():
            if param_name in result.params_schema["properties"]:
                result.params_schema["properties"][param_name].update(overrides)
            else:
                result.params_schema["properties"][param_name] = overrides

    return result


def _env_prefix_from_tool_id(tool_id: str | None) -> str | None:
    if not tool_id:
        return None
    if tool_id.startswith("tools."):
        return tool_id.split(".", 1)[1]
    return tool_id


def load_manifest_file(path: Path) -> tuple[ToolManifest | None, ManifestDiagnostic | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, ManifestDiagnostic(path=path, tool_id=None, errors=[str(exc)])

    try:
        data = yaml.safe_load(raw)
    except Exception as exc:  # noqa: BLE001
        return None, ManifestDiagnostic(
            path=path, tool_id=None, errors=[f"YAML parse error: {exc}"]
        )

    if not isinstance(data, dict):
        return None, ManifestDiagnostic(
            path=path, tool_id=None, errors=["Manifest must be a mapping"]
        )

    checksum = _sha256_bytes(raw)
    tool_id = data.get("tool_id") if isinstance(data.get("tool_id"), str) else None

    try:
        manifest = ToolManifest.model_validate(
            {
                **data,
                "manifest_path": path,
                "manifest_checksum": checksum,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return None, ManifestDiagnostic(path=path, tool_id=tool_id, errors=[str(exc)])

    warnings = []

    # Discover functions from dynamic sources if present
    if manifest.dynamic_sources:
        try:
            discovered_metadata = discover_functions(manifest, ADAPTER_REGISTRY)

            # Convert FunctionMetadata to Function objects
            for meta in discovered_metadata:
                inputs, outputs = _map_io_pattern_to_ports(meta.io_pattern)

                # Filter out port names from parameters (T109)
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
                filtered_params = {
                    k: v
                    for k, v in meta.parameters.items()
                    if k not in port_names and v.type not in artifact_types
                }
                params_schema = _parameters_to_json_schema(filtered_params)

                env_prefix = _env_prefix_from_tool_id(manifest.tool_id)
                fn_id = meta.fn_id
                if env_prefix and not fn_id.startswith(f"{env_prefix}."):
                    fn_id = f"{env_prefix}.{fn_id}"

                function = Function(
                    fn_id=fn_id,
                    tool_id=manifest.tool_id,
                    name=meta.name,
                    description=meta.description,
                    tags=meta.tags,
                    inputs=inputs,
                    outputs=outputs,
                    params_schema=params_schema,
                    hints=meta.hints,
                    introspection_source=meta.source_adapter,
                )
                manifest.functions.append(function)
        except Exception as e:  # noqa: BLE001
            # If discovery fails (e.g., adapter not registered), continue with
            # manifest loading. This allows manifests to be loaded before adapters
            # are fully implemented, and enables graceful degradation.
            warnings.append(f"Discovery failed for {path}: {e}")
            import traceback

            traceback.print_exc()

    # Apply overlays
    if manifest.function_overlays:
        discovered_fn_ids = {f.fn_id for f in manifest.functions}
        for fn_id, overlay in manifest.function_overlays.items():
            if fn_id not in discovered_fn_ids:
                warnings.append(f"Overlay target {fn_id} not found in tool {manifest.tool_id}")
                continue

            # Find the function and replace it with the merged version
            for i, function in enumerate(manifest.functions):
                if function.fn_id == fn_id:
                    manifest.functions[i] = merge_function_overlay(function, overlay)
                    break

    diag = None
    if warnings:
        diag = ManifestDiagnostic(path=path, tool_id=manifest.tool_id, errors=[], warnings=warnings)

    return manifest, diag


def discover_manifest_paths(roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        paths.extend(sorted(root.rglob("*.yaml")))
        paths.extend(sorted(root.rglob("*.yml")))
    # De-dup
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def load_manifests(roots: list[Path]) -> tuple[list[ToolManifest], list[ManifestDiagnostic]]:
    manifests: list[ToolManifest] = []
    diagnostics: list[ManifestDiagnostic] = []

    for path in discover_manifest_paths(roots):
        manifest, diag = load_manifest_file(path)
        if manifest is not None:
            manifests.append(manifest)
        elif diag is not None:
            diagnostics.append(diag)

    return manifests, diagnostics
