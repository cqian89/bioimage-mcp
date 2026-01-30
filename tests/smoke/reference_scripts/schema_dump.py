from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.storage.sqlite import connect


def canonicalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove documentation fields from schema for comparison."""
    if not isinstance(schema, dict):
        return schema

    # Fields to ignore in comparison
    ignore_fields = {"description", "title", "examples", "default"}

    result = {k: v for k, v in schema.items() if k not in ignore_fields}

    if "properties" in result:
        result["properties"] = {k: canonicalize_schema(v) for k, v in result["properties"].items()}

    if "items" in result:
        result["items"] = canonicalize_schema(result["items"])

    return result


def dump_runtime_schema(fn_id: str) -> dict[str, Any] | None:
    config = load_config()
    conn = connect(config)

    try:
        with DiscoveryService(conn):
            # We need to find the manifest to get the entrypoint and env_id
            manifests, _ = load_manifests(config.tool_manifest_roots)
            manifest = next(
                (m for m in manifests if any(fn.fn_id == fn_id for fn in m.functions)),
                None,
            )

            if not manifest:
                print(f"Error: No manifest found for {fn_id}", file=sys.stderr)
                return None

            entrypoint = manifest.entrypoint
            entry_path = Path(entrypoint)
            if not entry_path.is_absolute():
                candidate = manifest.manifest_path.parent / entry_path
                if candidate.exists():
                    entrypoint = str(candidate)

            request = {
                "id": "meta.describe",
                "params": {"target_fn": fn_id},
                "inputs": {},
            }

            response, log_text, exit_code = execute_tool(
                entrypoint=entrypoint,
                request=request,
                env_id=manifest.env_id,
            )

            if not response.get("ok"):
                print(
                    f"Error calling meta.describe for {fn_id}: {response.get('error')}",
                    file=sys.stderr,
                )
                print(f"Log: {log_text}", file=sys.stderr)
                return None

            result = response.get("result") or {}
            return result
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Dump runtime schema for bioimage-mcp functions")
    parser.add_argument("fn_ids", nargs="+", help="Function IDs to dump")
    parser.add_argument("--canonical", action="store_true", help="Canonicalize output")

    args = parser.parse_args()

    output = {}
    for fn_id in args.fn_ids:
        schema = dump_runtime_schema(fn_id)
        if schema:
            if args.canonical:
                if "params_schema" in schema:
                    schema["params_schema"] = canonicalize_schema(schema["params_schema"])
            output[fn_id] = schema

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
