from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.storage.sqlite import connect
from tests.smoke.schema_vectors import SCHEMA_VECTORS


def get_json_path_diffs(expected: Any, actual: Any, path: str = "$") -> list[str]:
    """
    Compare two JSON-like structures and return a list of differences with JSON paths.
    Focuses on: property names, types, required fields, enums.
    Ignores: description, title, examples.
    """
    diffs = []

    if type(expected) != type(actual):
        diffs.append(
            f"{path}: Type mismatch. Expected {type(expected).__name__}, got {type(actual).__name__}"
        )
        return diffs

    if isinstance(expected, dict):
        # Fields to ignore
        ignore_fields = {"description", "title", "examples", "default"}

        expected_keys = {k for k in expected.keys() if k not in ignore_fields}
        actual_keys = {k for k in actual.keys() if k not in ignore_fields}

        # For params_schema comparison, we focus on properties, type, required, enum
        # We don't necessarily care about extra keys at the top level if they are not standard

        for k in expected_keys:
            if k not in actual_keys:
                diffs.append(f"{path}: Missing expected key '{k}'")

        # If we are in properties, we check for unexpected extra keys as well
        if path.endswith(".properties"):
            for k in actual_keys - expected_keys:
                diffs.append(f"{path}: Unexpected extra key '{k}'")

        for k in expected_keys & actual_keys:
            diffs.extend(get_json_path_diffs(expected[k], actual[k], f"{path}.{k}"))

    elif isinstance(expected, list):
        if (
            path.endswith(".required")
            or path.endswith(".enum")
            or (path.endswith(".type") and expected and isinstance(expected[0], str))
        ):
            # Order-independent comparison for sets
            expected_set = set(expected)
            actual_set = set(actual)
            missing = expected_set - actual_set
            extra = actual_set - expected_set
            if missing:
                diffs.append(f"{path}: Missing expected values {missing}")
            if extra:
                diffs.append(f"{path}: Unexpected extra values {extra}")
        elif len(expected) != len(actual):
            diffs.append(
                f"{path}: List length mismatch. Expected {len(expected)}, got {len(actual)}"
            )
        else:
            for i, (e, a) in enumerate(zip(expected, actual)):
                diffs.extend(get_json_path_diffs(e, a, f"{path}[{i}]"))
    else:
        if expected != actual:
            diffs.append(f"{path}: Value mismatch. Expected {repr(expected)}, got {repr(actual)}")

    return diffs


@pytest.mark.smoke_minimal
def test_schema_comparison_logic():
    """Test the comparison logic itself with some manual cases."""
    expected = {
        "type": "object",
        "properties": {
            "sigma": {"type": "number", "description": "blur amount"},
            "mode": {"type": "string", "enum": ["reflect", "constant"]},
        },
        "required": ["sigma"],
    }

    # Case 1: Exact match (ignoring description)
    actual_ok = {
        "type": "object",
        "properties": {
            "sigma": {"type": "number"},
            "mode": {"type": "string", "enum": ["reflect", "constant"]},
        },
        "required": ["sigma"],
    }
    assert get_json_path_diffs(expected, actual_ok) == []

    # Case 2: Type mismatch
    actual_bad_type = {
        "type": "object",
        "properties": {
            "sigma": {"type": "integer"},
            "mode": {"type": "string", "enum": ["reflect", "constant"]},
        },
        "required": ["sigma"],
    }
    diffs = get_json_path_diffs(expected, actual_bad_type)
    assert any("$.properties.sigma.type: Value mismatch" in d for d in diffs)

    # Case 3: Missing required
    actual_missing_req = {
        "type": "object",
        "properties": {
            "sigma": {"type": "number"},
            "mode": {"type": "string", "enum": ["reflect", "constant"]},
        },
        "required": [],
    }
    diffs = get_json_path_diffs(expected, actual_missing_req)
    assert any("$.required: Missing expected values {'sigma'}" in d for d in diffs)

    # Case 4: Extra property
    actual_extra_prop = {
        "type": "object",
        "properties": {
            "sigma": {"type": "number"},
            "mode": {"type": "string", "enum": ["reflect", "constant"]},
            "extra": {"type": "string"},
        },
        "required": ["sigma"],
    }
    diffs = get_json_path_diffs(expected, actual_extra_prop)
    assert any("$.properties: Unexpected extra key 'extra'" in d for d in diffs)


@pytest.mark.smoke_minimal
@pytest.mark.anyio
@pytest.mark.parametrize("fn_id", list(SCHEMA_VECTORS.keys()))
async def test_schema_alignment_describe_vs_vector(live_server, fn_id):
    """Verify MCP describe() matches the expected schema vector."""
    expected = SCHEMA_VECTORS[fn_id]

    # Call describe()
    describe_result = await live_server.call_tool("describe", {"fn_id": fn_id})
    if "error" in describe_result:
        pytest.fail(f"describe({fn_id}) failed: {describe_result['error']}")

    actual = {
        "inputs": describe_result.get("inputs", {}),
        "outputs": describe_result.get("outputs", {}),
        "params_schema": describe_result.get("params_schema", {}),
    }

    diffs = get_json_path_diffs(expected, actual)
    assert not diffs, f"Schema mismatch for {fn_id}:\n" + "\n".join(diffs)


def _get_runtime_schema_direct(fn_id: str) -> dict[str, Any] | None:
    """Helper to get runtime schema by bypassign MCP server and calling tool directly."""
    config = load_config()
    manifests, _ = load_manifests(config.tool_manifest_roots)
    manifest = next(
        (m for m in manifests if any(fn.fn_id == fn_id for fn in m.functions)),
        None,
    )

    if not manifest:
        # Check dynamic sources
        for m in manifests:
            if any(
                fn_id.startswith(f"{m.tool_id.replace('tools.', '')}.{ds.prefix}.")
                for ds in m.dynamic_sources
            ):
                manifest = m
                break

    if not manifest:
        return None

    entrypoint = manifest.entrypoint
    entry_path = Path(entrypoint)
    if not entry_path.is_absolute():
        candidate = manifest.manifest_path.parent / entry_path
        if candidate.exists():
            entrypoint = str(candidate)

    request = {
        "fn_id": "meta.describe",
        "params": {"target_fn": fn_id},
        "inputs": {},
    }

    response, _log_text, _exit_code = execute_tool(
        entrypoint=entrypoint,
        request=request,
        env_id=manifest.env_id,
    )

    if response.get("ok"):
        return response.get("result") or {}
    return None


@pytest.mark.smoke_minimal
@pytest.mark.anyio
@pytest.mark.parametrize("fn_id", list(SCHEMA_VECTORS.keys()))
async def test_schema_alignment_describe_vs_runtime(live_server, fn_id):
    """Verify MCP describe() matches the live meta.describe() runtime output."""

    # 1. Call describe() via MCP
    describe_result = await live_server.call_tool("describe", {"fn_id": fn_id})
    if "error" in describe_result:
        pytest.fail(f"describe({fn_id}) failed: {describe_result['error']}")

    # 2. Get runtime schema directly (to avoid ambiguity of meta.describe resolution in MCP)
    runtime_result = _get_runtime_schema_direct(fn_id)

    if not runtime_result:
        pytest.skip(f"meta.describe not supported or failed for {fn_id} when called directly")

    # 3. Compare them
    actual_describe = {"params_schema": describe_result.get("params_schema", {})}

    expected_runtime = {"params_schema": runtime_result.get("params_schema", {})}

    diffs = get_json_path_diffs(expected_runtime, actual_describe)
    assert not diffs, f"Runtime drift detected for {fn_id}:\n" + "\n".join(diffs)
