from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from bioimage_mcp.registry.diagnostics import ManifestDiagnostic
from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
from bioimage_mcp.registry.dynamic.discovery import discover_functions
from bioimage_mcp.registry.dynamic.models import IOPattern, ParameterSchema
from bioimage_mcp.registry.manifest_schema import Function, Port, ToolManifest


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
    else:
        # Default/Generic: single input/output
        inputs = [Port(name="input", artifact_type="BioImageRef")]
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

    # Discover functions from dynamic sources if present
    if manifest.dynamic_sources:
        try:
            discovered_metadata = discover_functions(manifest, ADAPTER_REGISTRY)

            # Convert FunctionMetadata to Function objects
            for meta in discovered_metadata:
                inputs, outputs = _map_io_pattern_to_ports(meta.io_pattern)
                params_schema = _parameters_to_json_schema(meta.parameters)

                function = Function(
                    fn_id=meta.fn_id,
                    tool_id=manifest.tool_id,
                    name=meta.name,
                    description=meta.description,
                    tags=meta.tags,
                    inputs=inputs,
                    outputs=outputs,
                    params_schema=params_schema,
                    introspection_source=meta.source_adapter,
                )
                manifest.functions.append(function)
        except Exception as e:  # noqa: BLE001
            # If discovery fails (e.g., adapter not registered), continue with
            # manifest loading. This allows manifests to be loaded before adapters
            # are fully implemented, and enables graceful degradation.
            print(f"Discovery failed for {manifest.manifest_path}: {e}")
            import traceback

            traceback.print_exc()
            pass

    return manifest, None


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
