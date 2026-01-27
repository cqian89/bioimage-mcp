from __future__ import annotations

from typing import Any


def normalize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Produces deterministically ordered schema output.

    Sorts object keys and ensures 'required' is a stable list ordering.
    """
    if not isinstance(schema, dict):
        return schema

    normalized = {}
    # Sort keys alphabetically
    for key in sorted(schema.keys()):
        value = schema[key]
        if key == "required" and isinstance(value, list):
            normalized[key] = sorted(value)
        elif isinstance(value, dict):
            normalized[key] = normalize_json_schema(value)
        elif isinstance(value, list):
            normalized[key] = [
                normalize_json_schema(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            normalized[key] = value

    return normalized
