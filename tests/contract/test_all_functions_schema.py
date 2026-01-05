from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import load_manifests


def _get_all_function_ids() -> list[str]:
    """Collect all function IDs from registered manifests."""
    manifests, _ = load_manifests([Path("tools")])
    fn_ids = []
    for manifest in manifests:
        for fn in manifest.functions:
            fn_ids.append(fn.fn_id)
    return fn_ids


@pytest.fixture(scope="module")
def all_functions() -> list[dict]:
    """Load all function definitions."""
    manifests, _ = load_manifests([Path("tools")])
    functions = []
    for manifest in manifests:
        for fn in manifest.functions:
            functions.append(
                {
                    "fn_id": fn.fn_id,
                    "name": fn.name,
                    "description": fn.description,
                    "inputs": fn.inputs,
                    "outputs": fn.outputs,
                    "params_schema": fn.params_schema,
                }
            )
    return functions


def test_all_functions_have_required_fields(all_functions: list[dict]) -> None:
    """Validate all registered functions have required schema fields."""
    missing_fields = []

    for fn in all_functions:
        fn_id = fn["fn_id"]

        # Check required fields
        if not fn.get("name"):
            missing_fields.append(f"{fn_id}: missing 'name'")
        if not fn.get("description"):
            missing_fields.append(f"{fn_id}: missing 'description'")
        if fn.get("params_schema") is None:
            missing_fields.append(f"{fn_id}: missing 'params_schema'")

    if missing_fields:
        pytest.fail("Functions missing required fields:\n" + "\n".join(missing_fields))


def test_all_params_schemas_are_valid_json_schema(all_functions: list[dict]) -> None:
    """Validate params_schema is a valid JSON Schema object."""
    invalid_schemas = []

    for fn in all_functions:
        fn_id = fn["fn_id"]
        schema = fn.get("params_schema")

        if schema is None:
            continue

        if not isinstance(schema, dict):
            invalid_schemas.append(f"{fn_id}: params_schema is not a dict")
            continue

        if schema.get("type") != "object":
            invalid_schemas.append(f"{fn_id}: params_schema.type must be 'object'")

    if invalid_schemas:
        pytest.fail("Invalid schemas:\n" + "\n".join(invalid_schemas))


def test_all_json_schema_types_are_correct(all_functions: list[dict]) -> None:
    """Validate JSON Schema types for parameters (T108)."""
    invalid_types = []

    for fn in all_functions:
        fn_id = fn["fn_id"]
        schema = fn.get("params_schema", {})
        properties = schema.get("properties", {})

        for prop_name, prop_info in properties.items():
            if not isinstance(prop_info, dict):
                continue

            js_type = prop_info.get("type")
            default_val = prop_info.get("default")

            if default_val is None:
                continue

            # Check booleans
            if isinstance(default_val, bool):
                if js_type != "boolean":
                    invalid_types.append(
                        f"{fn_id}: param '{prop_name}' has boolean default {default_val} but type '{js_type}' (expected 'boolean')"
                    )
            # Check numbers (ints and floats)
            # Note: bool is a subclass of int in Python, so check bool first
            elif isinstance(default_val, (int, float)):
                if js_type not in ("number", "integer"):
                    invalid_types.append(
                        f"{fn_id}: param '{prop_name}' has numeric default {default_val} but type '{js_type}' (expected 'number' or 'integer')"
                    )

    if invalid_types:
        summary = f"Found {len(invalid_types)} incorrect JSON Schema types."
        details = "\n".join(invalid_types[:50])  # Show up to 50
        if len(invalid_types) > 50:
            details += f"\n... and {len(invalid_types) - 50} more"
        pytest.fail(f"{summary}\n{details}")


def test_artifact_ports_not_in_params_schema(all_functions: list[dict]) -> None:
    """Validate artifact ports never appear inside params_schema (T109)."""
    violations = []

    for fn in all_functions:
        fn_id = fn["fn_id"]
        schema = fn.get("params_schema", {})
        properties = schema.get("properties", {})

        # Collect port names from inputs and outputs
        port_names = set()
        for port in fn.get("inputs", []):
            if hasattr(port, "name"):
                port_names.add(port.name)
            elif isinstance(port, dict):
                port_names.add(port["name"])

        for port in fn.get("outputs", []):
            if hasattr(port, "name"):
                port_names.add(port.name)
            elif isinstance(port, dict):
                port_names.add(port["name"])

        # Check for overlaps
        for port_name in port_names:
            if port_name in properties:
                violations.append(
                    f"{fn_id}: artifact port '{port_name}' also appears in params_schema"
                )

    if violations:
        pytest.fail("Artifact ports found in params_schema:\n" + "\n".join(violations))


def test_function_count_report(all_functions: list[dict]) -> None:
    """Report total functions tested."""
    print(f"\nTotal functions validated: {len(all_functions)}")
    assert len(all_functions) > 0, "No functions found in registry"
