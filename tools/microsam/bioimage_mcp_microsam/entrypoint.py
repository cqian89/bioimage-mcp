#!/usr/bin/env python3
"""Microsam tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Setup paths to include src and tools
BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent.parent
REPO_ROOT = TOOLS_ROOT.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
if str(BASE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BASE_DIR.parent))

from bioimage_mcp_microsam.device import select_device  # noqa: E402

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-microsam"

# Global memory artifacts (for materialize/evict compatibility)
_MEMORY_ARTIFACTS: dict[str, Any] = {}
_SESSION_ID: str | None = None
_ENV_ID: str | None = None


def _initialize_worker(session_id: str, env_id: str) -> None:
    global _SESSION_ID, _ENV_ID
    _SESSION_ID = session_id
    _ENV_ID = env_id


def handle_meta_list(params: dict[str, Any]) -> dict[str, Any]:
    """Out-of-process function discovery for microsam tool pack."""
    import hashlib

    import yaml

    from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
    from bioimage_mcp.registry.dynamic.cache import IntrospectionCache
    from bioimage_mcp.registry.dynamic.discovery import discover_functions
    from bioimage_mcp.registry.manifest_schema import ToolManifest

    manifest_path = BASE_DIR.parent / "manifest.yaml"
    try:
        raw = manifest_path.read_bytes()
        manifest_data = yaml.safe_load(raw)
        checksum = hashlib.sha256(raw).hexdigest()

        manifest = ToolManifest.model_validate(
            {
                **manifest_data,
                "manifest_path": manifest_path,
                "manifest_checksum": checksum,
            }
        )

        # Wire introspection cache
        cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id
        cache = IntrospectionCache(cache_dir)

        # Project root discovery
        curr = manifest_path.parent
        project_root = None
        for _ in range(5):
            if (curr / "envs").exists() or (curr / "pyproject.toml").exists():
                project_root = curr
                break
            curr = curr.parent

        try:
            from bioimage_mcp.registry.dynamic.adapters import populate_default_adapters

            populate_default_adapters()
            print(f"DEBUG: ADAPTER_REGISTRY keys: {list(ADAPTER_REGISTRY.keys())}", file=sys.stderr)

            discovered = discover_functions(
                manifest, ADAPTER_REGISTRY, cache=cache, project_root=project_root
            )
        except ValueError as e:
            if "Unknown adapter" in str(e):
                discovered = []
            else:
                raise

        from bioimage_mcp.registry.engine import DiscoveryEngine

        functions = []
        for meta in discovered:
            summary = meta.description.split("\n")[0] if meta.description else ""
            fn_dict = {
                "id": meta.fn_id,
                "name": meta.name,
                "module": meta.module,
                "summary": summary,
                "io_pattern": meta.io_pattern.value,
                "description": meta.description,
                "parameters": {k: v.model_dump() for k, v in meta.parameters.items()},
                "params_schema": DiscoveryEngine.parameters_to_json_schema(meta.parameters),
                "returns": meta.returns,
                "source_adapter": meta.source_adapter,
            }
            functions.append(fn_dict)

        return {
            "ok": True,
            "result": {
                "functions": functions,
                "tool_version": TOOL_VERSION,
                "introspection_source": "dynamic_discovery",
            },
        }
    except Exception as exc:
        logger.error(f"Discovery failed: {exc}")
        return {
            "ok": True,
            "result": {
                "functions": [],
                "tool_version": TOOL_VERSION,
                "introspection_source": "fallback_empty",
                "warning": f"Discovery failed: {exc}",
            },
        }


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    target_fn = params.get("target_fn", "")
    if not target_fn:
        return {"ok": False, "error": "Missing target_fn"}

    try:
        import hashlib

        import yaml

        from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache
        from bioimage_mcp.registry.dynamic.discovery import discover_functions
        from bioimage_mcp.registry.engine import DiscoveryEngine
        from bioimage_mcp.registry.manifest_schema import ToolManifest

        manifest_path = BASE_DIR.parent / "manifest.yaml"
        raw = manifest_path.read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        manifest_data = yaml.safe_load(raw)
        manifest = ToolManifest.model_validate(
            {
                **manifest_data,
                "manifest_path": manifest_path,
                "manifest_checksum": checksum,
            }
        )

        cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id
        cache = IntrospectionCache(cache_dir)

        try:
            discovered = discover_functions(manifest, ADAPTER_REGISTRY, cache=cache)
        except ValueError as e:
            if "Unknown adapter" in str(e):
                discovered = []
            else:
                raise

        # Strip prefix if present for matching
        search_fn = target_fn
        if search_fn.startswith("micro_sam."):
            search_fn = search_fn[10:]

        meta = next((m for m in discovered if m.fn_id == search_fn or m.fn_id == target_fn), None)
        if meta is not None:
            schema = DiscoveryEngine.parameters_to_json_schema(meta.parameters)
            return {
                "ok": True,
                "result": {
                    "params_schema": schema,
                    "tool_version": TOOL_VERSION,
                    "introspection_source": "dynamic_discovery",
                },
            }
    except Exception as exc:
        logger.warning("Dynamic discovery for %s failed: %s", target_fn, exc)

    # Fallback to hardcoded meta.describe if dynamic fails or isn't implemented yet
    if target_fn == "meta.describe":
        return {
            "ok": True,
            "result": {
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "target_fn": {
                            "type": "string",
                            "description": "The function id to describe",
                        }
                    },
                    "required": ["target_fn"],
                },
                "introspection_source": "static",
            },
        }

    return {
        "ok": False,
        "error": {
            "code": "NOT_FOUND",
            "message": f"Function {target_fn} not found in tools.micro_sam",
        },
    }


def process_execute_request(request: dict[str, Any]) -> dict[str, Any]:
    req_id = request.get("id") or request.get("fn_id")
    params = request.get("params", {})
    tool_config = request.get("tool_config", {})
    ordinal = request.get("ordinal")

    # Resolve runtime device
    device_pref = tool_config.get("microsam", {}).get("device", "auto")
    try:
        # We use strict=False for meta.* to avoid blocking discovery
        is_meta = req_id in ("meta.list", "meta.describe")
        select_device(device_pref, strict=not is_meta)
    except RuntimeError as e:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "DEVICE_UNAVAILABLE",
                "message": str(e),
                "details": [
                    {
                        "path": "microsam.device",
                        "hint": (
                            "Set microsam.device to 'auto' or install a compatible GPU profile."
                        ),
                    }
                ],
            },
        }

    if req_id == "meta.list":
        result = handle_meta_list(params)
    elif req_id == "meta.describe":
        result = handle_meta_describe(params)
    elif req_id.startswith("micro_sam."):
        from bioimage_mcp.errors import BioimageMcpError
        from bioimage_mcp.registry.dynamic.adapters.microsam import MicrosamAdapter

        adapter = MicrosamAdapter()
        try:
            inputs = request.get("inputs", {})
            work_dir = Path(request.get("work_dir", "."))

            # Only inject device if not already in params and if the target function likely needs it
            # (Or let the adapter handle it based on param_names)
            device_pref = tool_config.get("microsam", {}).get("device", "auto")

            result_artifacts = adapter.execute(
                fn_id=req_id,
                inputs=inputs,
                params=params,
                work_dir=work_dir,
                hints={"device": device_pref},
            )

            # Pack results into outputs dict
            if len(result_artifacts) == 1:
                outputs = {"output": result_artifacts[0]}
            else:
                outputs = {f"output_{i}": art for i, art in enumerate(result_artifacts)}

            response = {
                "command": "execute_result",
                "ok": True,
                "ordinal": ordinal,
                "id": req_id,
                "outputs": outputs,
                "log": "ok",
            }

            if adapter.warnings:
                response["warnings"] = adapter.warnings

            return response

        except BioimageMcpError as e:
            return {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "id": req_id,
                "error": {
                    "code": e.code,
                    "message": str(e),
                    "details": getattr(e, "details", None),
                },
                "log": f"Error: {e}",
            }
        except Exception as e:
            logger.exception(f"Execution failed for {req_id}")
            return {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "id": req_id,
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(e),
                },
                "log": f"Error: {e}",
            }
    else:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "id": req_id,
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": f"Function {req_id} is not implemented yet in Phase 22",
            },
        }

    response = {
        "command": "execute_result",
        "ok": result.get("ok", False),
        "ordinal": ordinal,
        "id": req_id,
    }
    if result.get("ok"):
        response["outputs"] = {"result": result.get("result")}
        response["log"] = "ok"
    else:
        response["error"] = {"message": result.get("error", "Unknown error")}
        response["log"] = f"Error: {result.get('error')}"

    return response


def main():
    import os
    import select

    # Initialize worker identity
    session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
    env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-microsam")
    _initialize_worker(session_id, env_id)

    # If stdin has data, handle it as a single request and exit without ready handshake
    # (Important for one-shot execution like meta.list)
    if not sys.stdin.isatty():
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            line = sys.stdin.readline()
            if line.strip():
                try:
                    request = json.loads(line)
                    response = process_execute_request(request)
                    print(json.dumps(response), flush=True)
                    return
                except json.JSONDecodeError:
                    pass

    # Persistent NDJSON loop
    ready_message = json.dumps({"command": "ready", "version": TOOL_VERSION})
    print(ready_message, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print(
                json.dumps({"command": "error", "ok": False, "error": {"message": "Invalid JSON"}}),
                flush=True,
            )
            continue

        cmd = request.get("command")
        if cmd == "execute":
            response = process_execute_request(request)
            print(json.dumps(response), flush=True)
        elif cmd == "shutdown":
            _MEMORY_ARTIFACTS.clear()
            print(
                json.dumps(
                    {"command": "shutdown_ack", "ok": True, "ordinal": request.get("ordinal")}
                ),
                flush=True,
            )
            break
        elif cmd in ("materialize", "evict"):
            # Minimal compatibility handlers
            print(
                json.dumps(
                    {
                        "command": f"{cmd}_result",
                        "ok": False,
                        "ordinal": request.get("ordinal"),
                        "error": {"message": "Not implemented"},
                    }
                ),
                flush=True,
            )
        else:
            print(
                json.dumps(
                    {
                        "command": "error",
                        "ok": False,
                        "error": {"message": f"Unknown command: {cmd}"},
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
