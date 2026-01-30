"""Introspection utilities for dynamic parameter schema extraction.

This module provides utilities to extract JSON Schema from Python function
signatures and argparse parsers, supporting the meta.describe protocol.

See specs/001-cellpose-pipeline/meta-describe-protocol.md for protocol details.
"""

from __future__ import annotations

import argparse
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, get_type_hints

import docstring_parser
from pydantic import TypeAdapter

if TYPE_CHECKING:
    pass

# Map Python types to JSON Schema types
TYPE_MAP: dict[type, str] = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object",
}

# Type inference map for common parameter name patterns
PARAM_TYPE_PATTERNS = {
    "axis": "integer",  # Runtime arrays are numpy ndarrays (int indices only)
    "harmonic": "integer",
    "radius": "integer",
    "sigma": "number",
    "size": "integer",
    "limit": "number",
    "clip": "boolean",
    "apply": "boolean",
    "preserve_range": "boolean",
    "anti_aliasing": "boolean",
}

# Artifact port names to omit from params_schema
ARTIFACT_PORTS = {
    "image",
    "labels",
    "table",
    "signal",
    "mask",
    "model",
    "artifact",
    "output",
    "input",
    "labels_path",
    "image_path",
    "label_image",
    "intensity_image",
}


def is_artifact_param(name: str, type_hint: Any) -> bool:
    """Check if a parameter is likely an artifact port based on name or type."""
    if name.lower() in ARTIFACT_PORTS:
        return True
    type_str = str(type_hint)
    artifact_types = {"ArtifactRef", "BioImageRef", "NativeOutputRef", "ObjectRef"}
    return any(at in type_str for at in artifact_types)


def schema_from_descriptions(descriptions: dict[str, str]) -> dict[str, Any]:
    """Generate JSON Schema from curated parameter descriptions.

    Used when function signature introspection returns empty properties.
    Infers types from common parameter naming patterns.

    Args:
        descriptions: Parameter descriptions {param_name: description}

    Returns:
        JSON Schema dict with 'type', 'properties' fields.
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
    }

    for name, desc in sorted(descriptions.items()):
        prop: dict[str, Any] = {"description": desc}

        # Infer type from parameter name patterns
        for pattern, json_type in PARAM_TYPE_PATTERNS.items():
            if pattern in name.lower():
                prop["type"] = json_type
                break

        schema["properties"][name] = prop

    return schema


def introspect_python_api(
    func: Callable[..., Any],
    descriptions: dict[str, str],
    exclude_params: set[str] | None = None,
) -> dict[str, Any]:
    """Generate JSON Schema from a Python function signature.

    Args:
        func: The function to introspect (e.g., CellposeModel.eval)
        descriptions: Curated parameter descriptions {param_name: description}
        exclude_params: Parameter names to exclude (e.g., {'self', 'x'})

    Returns:
        JSON Schema dict with 'type', 'properties', and 'required' fields
    """
    exclude = exclude_params if exclude_params is not None else {"self", "cls"}
    sig = inspect.signature(func)

    # Try to get type hints (may fail for some functions)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    # Parse docstring for parameter descriptions
    doc = docstring_parser.parse(func.__doc__ or "")
    doc_params = {p.arg_name: p.description for p in doc.params if p.arg_name}

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for name, param in sig.parameters.items():
        if name in exclude:
            continue

        # Skip *args and **kwargs
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        # Skip artifact ports
        type_hint = hints.get(name, param.annotation)
        if is_artifact_param(name, type_hint):
            continue

        prop: dict[str, Any] = {}

        # Add description (curated > docstring > fallback)
        desc = descriptions.get(name) or doc_params.get(name)
        has_curated_or_doc = desc is not None
        if desc:
            prop["description"] = desc
        else:
            module_name = getattr(func, "__module__", "unknown")
            prop["description"] = f"See {module_name} documentation."

        # Add default value
        if param.default is not inspect.Parameter.empty:
            # Handle numpy types and other non-JSON-serializable defaults
            default = param.default
            if hasattr(default, "item"):  # numpy scalar
                default = default.item()
            if default is not None:
                prop["default"] = default
        else:
            # No default = required parameter
            schema["required"].append(name)

        # Map type annotation to JSON Schema type
        if type_hint is not inspect.Parameter.empty:
            try:
                # Pydantic v2 TypeAdapter for high-fidelity schema
                param_json_schema = TypeAdapter(type_hint).json_schema()
                # Clean up schema for parameter use
                param_json_schema.pop("title", None)
                if has_curated_or_doc:
                    param_json_schema.pop("description", None)
                prop.update(param_json_schema)
            except Exception:
                # Fallback to manual mapping if TypeAdapter fails
                origin = getattr(type_hint, "__origin__", type_hint)
                if origin in TYPE_MAP:
                    prop["type"] = TYPE_MAP[origin]
                elif type_hint in TYPE_MAP:
                    prop["type"] = TYPE_MAP[type_hint]

        schema["properties"][name] = prop

    # Fallback to descriptions if introspection yielded no properties
    if not schema["properties"] and descriptions:
        return schema_from_descriptions(descriptions)

    # Ensure deterministic output
    sorted_properties = {k: schema["properties"][k] for k in sorted(schema["properties"].keys())}
    schema["properties"] = sorted_properties

    # Final cleanup of required fields: must exist in properties and omit if empty
    schema["required"] = [r for r in schema["required"] if r in schema["properties"]]
    if schema["required"]:
        schema["required"].sort()
    else:
        schema.pop("required", None)

    return schema


def introspect_argparse(
    parser: argparse.ArgumentParser,
    descriptions: dict[str, str],
    exclude_dests: set[str] | None = None,
) -> dict[str, Any]:
    """Generate JSON Schema from an argparse ArgumentParser.

    Args:
        parser: The argument parser to introspect
        descriptions: Curated parameter descriptions {dest_name: description}
        exclude_dests: Destination names to exclude (e.g., {'help', 'version'})

    Returns:
        JSON Schema dict with 'type', 'properties', and 'required' fields
    """
    exclude = exclude_dests if exclude_dests is not None else {"help", "version"}

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for action in parser._actions:  # noqa: SLF001
        if action.dest in exclude:
            continue

        # Skip positional arguments that are typically file paths
        if not action.option_strings:
            continue

        prop: dict[str, Any] = {}

        # Add description (curated takes precedence, then argparse help)
        if action.dest in descriptions:
            prop["description"] = descriptions[action.dest]
        elif action.help and action.help != argparse.SUPPRESS:
            prop["description"] = action.help
        else:
            prop["description"] = "See tool documentation."

        # Add default value
        if action.default is not None and action.default != argparse.SUPPRESS:
            prop["default"] = action.default

        # Add choices as enum
        if action.choices:
            prop["enum"] = list(action.choices)

        # Map argparse type to JSON Schema type
        if action.type is not None:
            if action.type is int:
                prop["type"] = "integer"
            elif action.type is float:
                prop["type"] = "number"
            elif action.type is str:
                prop["type"] = "string"
        elif isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            prop["type"] = "boolean"
            prop["default"] = False
        elif isinstance(action, argparse._StoreFalseAction):  # noqa: SLF001
            prop["type"] = "boolean"
            prop["default"] = True

        # Check if required
        if action.required:
            schema["required"].append(action.dest)

        schema["properties"][action.dest] = prop

    # Ensure deterministic output
    sorted_properties = {k: schema["properties"][k] for k in sorted(schema["properties"].keys())}
    schema["properties"] = sorted_properties

    # Final cleanup of required fields: must exist in properties and omit if empty
    schema["required"] = [r for r in schema["required"] if r in schema["properties"]]
    if schema["required"]:
        schema["required"].sort()
    else:
        schema.pop("required", None)

    return schema
