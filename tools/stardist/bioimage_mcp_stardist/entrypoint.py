#!/usr/bin/env python3
"""StarDist tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import select
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Suppress TensorFlow noise
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Path setup
BASE_DIR = Path(__file__).resolve().parent
STARDIST_TOOL_ROOT = BASE_DIR.parent
if str(STARDIST_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(STARDIST_TOOL_ROOT))

# Project root for bioimage_mcp imports
REPO_ROOT = STARDIST_TOOL_ROOT.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioimage_mcp.registry.dynamic.cache import IntrospectionCache
from bioimage_mcp.registry.dynamic.discovery import discover_functions
from bioimage_mcp.registry.manifest_schema import ToolManifest
from bioimage_mcp_stardist.dynamic_discovery import StarDistAdapter

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-stardist"

_SESSION_ID: str | None = None
_ENV_ID: str | None = None
_WORK_DIR: Path = Path.cwd()

# Global memory artifact storage (for ObjectRefs)
_OBJECT_CACHE: dict[str, Any] = {}


def _initialize_worker(session_id: str, env_id: str, work_dir: str | None = None) -> None:
    global _SESSION_ID, _ENV_ID, _WORK_DIR
    _SESSION_ID = session_id
    _ENV_ID = env_id
    if work_dir:
        _WORK_DIR = Path(work_dir)
    else:
        _WORK_DIR = Path(os.environ.get("BIOIMAGE_MCP_WORK_DIR", Path.cwd()))
    _WORK_DIR.mkdir(parents=True, exist_ok=True)


def _find_project_root(start: Path) -> Path | None:
    curr = start
    for _ in range(5):
        if (curr / "envs").exists() or (curr / "pyproject.toml").exists():
            return curr
        curr = curr.parent
    return None


def handle_meta_list(params: dict) -> dict:
    manifest_path = STARDIST_TOOL_ROOT / "manifest.yaml"
    with contextlib.redirect_stdout(sys.stderr):
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

            project_root = None
            env_root = os.environ.get("BIOIMAGE_MCP_PROJECT_ROOT")
            if env_root:
                p = Path(env_root)
                if p.is_dir():
                    project_root = p

            if project_root is None:
                project_root = _find_project_root(Path.cwd())

            if project_root is None:
                project_root = _find_project_root(STARDIST_TOOL_ROOT)

            cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id
            cache = IntrospectionCache(cache_dir)

            discovered = discover_functions(
                manifest, {"stardist": StarDistAdapter()}, cache=cache, project_root=project_root
            )

            functions = []
            for meta in discovered:
                summary = meta.description.split("\n")[0] if meta.description else ""
                functions.append(
                    {
                        "id": meta.fn_id,
                        "name": meta.name,
                        "module": meta.module,
                        "summary": summary,
                        "io_pattern": meta.io_pattern.value,
                    }
                )

            try:
                import stardist

                stardist_version = stardist.__version__
            except ImportError:
                stardist_version = "unknown"

            return {
                "ok": True,
                "result": {
                    "functions": functions,
                    "tool_version": stardist_version,
                    "introspection_source": "dynamic_discovery",
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"Discovery failed: {exc}"}


def handle_meta_describe(params: dict) -> dict:
    target_fn = params.get("target_fn")
    if not target_fn:
        return {"ok": False, "error": "target_fn required"}

    with contextlib.redirect_stdout(sys.stderr):
        try:
            # Resolver for StarDist callables
            if not target_fn.startswith("stardist."):
                return {"ok": False, "error": f"Unsupported target_fn: {target_fn}"}

            parts = target_fn.split(".")
            if len(parts) < 3:
                return {"ok": False, "error": f"Invalid target_fn format: {target_fn}"}

            module_name = ".".join(parts[:-2])
            class_name = parts[-2]
            method_name = parts[-1]

            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)

            if method_name == class_name:
                func = cls
            else:
                func = getattr(cls, method_name)

            from bioimage_mcp.registry.dynamic.introspection import Introspector
            from bioimage_mcp.registry.engine import DiscoveryEngine

            introspector = Introspector()
            meta = introspector.introspect(func, source_adapter="stardist")

            if "self" in meta.parameters:
                del meta.parameters["self"]

            params_schema = DiscoveryEngine.parameters_to_json_schema(meta.parameters)

            try:
                import stardist

                stardist_version = stardist.__version__
            except ImportError:
                stardist_version = "unknown"

            return {
                "ok": True,
                "result": {
                    "params_schema": params_schema,
                    "tool_version": stardist_version,
                    "introspection_source": "python_api",
                },
            }
        except Exception as e:
            return {"ok": False, "error": f"Introspection failed: {e}\n{traceback.format_exc()}"}


def _execute_stardist_function(fn_id: str, params: dict, inputs: dict) -> dict:
    """Execute a StarDist function with artifact resolution."""
    with contextlib.redirect_stdout(sys.stderr):
        try:
            # 1. Model Initialization (Constructor)
            if (
                "from_pretrained" in fn_id
                or fn_id.endswith(".StarDist2D")
                or fn_id.endswith(".StarDist3D")
            ):
                from stardist.models import StarDist2D, StarDist3D

                is_2d = "StarDist2D" in fn_id
                cls = StarDist2D if is_2d else StarDist3D

                name = params.get("name", "2D_versatile_fluo" if is_2d else "3D_demo")

                if "from_pretrained" in fn_id:
                    model = cls.from_pretrained(name)
                else:
                    # Direct constructor call (could take more params)
                    model = cls(**params)

                import uuid

                object_id = uuid.uuid4().hex
                session_id = _SESSION_ID or "default"
                uri = f"obj://{session_id}/{_ENV_ID or TOOL_ENV_NAME}/{object_id}"

                _OBJECT_CACHE[uri] = model

                return {
                    "ok": True,
                    "outputs": {
                        "model": {
                            "type": "ObjectRef",
                            "ref_id": object_id,
                            "uri": uri,
                            "format": "pickle",
                            "python_class": f"{cls.__module__}.{cls.__name__}",
                            "storage_type": "memory",
                            "created_at": datetime.now(UTC).isoformat(),
                            "metadata": {"name": name},
                        }
                    },
                }

            # 2. Inference
            if "predict_instances" in fn_id:
                from bioimage_mcp_stardist.ops.predict import run_predict

                # Resolve model ObjectRef
                model_ref = inputs.get("model", {})
                model_uri = model_ref.get("uri")
                if not model_uri or model_uri not in _OBJECT_CACHE:
                    return {
                        "ok": False,
                        "error": f"Model ObjectRef not found or invalid: {model_uri}",
                    }

                model = _OBJECT_CACHE[model_uri]

                # Run prediction
                outputs = run_predict(inputs, params, _WORK_DIR, model=model)
                return {"ok": True, "outputs": outputs}

            return {"ok": False, "error": f"Unknown function: {fn_id}"}

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "log": traceback.format_exc(),
            }


def _handle_request(request: dict) -> dict:
    global _WORK_DIR
    command = request.get("command")
    params = request.get("params", {})
    inputs = request.get("inputs", {})
    fn_id = request.get("id") or request.get("fn_id")
    ordinal = request.get("ordinal")
    work_dir = request.get("work_dir")

    if work_dir:
        _WORK_DIR = Path(work_dir)
        _WORK_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if command == "execute":
            if fn_id == "meta.list":
                res = handle_meta_list(params)
            elif fn_id == "meta.describe":
                res = handle_meta_describe(params)
            else:
                res = _execute_stardist_function(fn_id, params, inputs)

            if res.get("ok"):
                return {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": res.get("outputs") or {"result": res.get("result")},
                    "id": fn_id,
                }
            else:
                return {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": {"message": res.get("error")},
                    "id": fn_id,
                }

        elif command == "shutdown":
            _OBJECT_CACHE.clear()
            return {"command": "shutdown_ack", "ok": True, "ordinal": ordinal}

        else:
            return {
                "command": "error",
                "ok": False,
                "ordinal": ordinal,
                "error": {"message": f"Unknown command: {command}"},
                "id": fn_id,
            }

    except Exception as exc:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"message": str(exc)},
            "log": traceback.format_exc(),
            "id": fn_id,
        }


def main():
    _initialize_worker(
        os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default"),
        os.environ.get("BIOIMAGE_MCP_ENV_ID", TOOL_ENV_NAME),
        os.environ.get("BIOIMAGE_MCP_WORK_DIR"),
    )

    if sys.stdin.isatty():
        sys.stdout.write(json.dumps({"command": "ready", "version": TOOL_VERSION}) + "\n")
        sys.stdout.flush()
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = _handle_request(request)
                print(json.dumps(response), flush=True)
                if response.get("command") == "shutdown_ack":
                    break
            except json.JSONDecodeError:
                pass
    else:
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            line = sys.stdin.readline()
            if line.strip():
                try:
                    request = json.loads(line)
                    response = _handle_request(request)
                    print(json.dumps(response), flush=True)
                    if (
                        request.get("command") in ["execute", "shutdown"]
                        and response.get("command") != "shutdown_ack"
                    ):
                        for line in sys.stdin:
                            line = line.strip()
                            if not line:
                                continue
                            request = json.loads(line)
                            response = _handle_request(request)
                            print(json.dumps(response), flush=True)
                            if response.get("command") == "shutdown_ack":
                                break
                    return
                except json.JSONDecodeError:
                    pass

        sys.stdout.write(json.dumps({"command": "ready", "version": TOOL_VERSION}) + "\n")
        sys.stdout.flush()
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = _handle_request(request)
                print(json.dumps(response), flush=True)
                if response.get("command") == "shutdown_ack":
                    break
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    main()
