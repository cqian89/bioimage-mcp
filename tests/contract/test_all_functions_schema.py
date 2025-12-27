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


def test_function_count_report(all_functions: list[dict]) -> None:
    """Report total functions tested."""
    print(f"\nTotal functions validated: {len(all_functions)}")
    assert len(all_functions) > 0, "No functions found in registry"
