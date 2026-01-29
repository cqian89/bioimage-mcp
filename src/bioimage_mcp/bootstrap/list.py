from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.bootstrap.list_cache import (
    InstalledEnvsCache,
    ListToolsCache,
    get_cli_cache_dir,
)
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import discover_manifest_paths, load_manifests


def _get_installed_envs(manager_exe: str) -> set[str]:
    try:
        proc = subprocess.run(
            [manager_exe, "env", "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if proc.returncode != 0:
            return set()
        data = json.loads(proc.stdout)

        envs = set()
        # micromamba/conda --json output format: {"envs": ["/path/to/env", ...]}
        if "envs" in data and isinstance(data["envs"], list):
            for env_path in data["envs"]:
                # The last segment of the path is usually the env name
                envs.add(env_path.replace("\\", "/").split("/")[-1])
        return envs
    except Exception:
        return set()


def _render_list(tool_details: list[dict[str, Any]], json_output: bool) -> int:
    if json_output:
        print(json.dumps({"tools": tool_details}))
        return 0

    if not tool_details:
        print("No tools found in registry.")
        return 0

    print(
        f"{'Tool':<25} | {'Version':<10} | {'Status':<12} | {'Functions':<10} | {'Introspection':<15}"
    )
    print("-" * 85)
    for t in tool_details:
        status_str = f"{t['status_char']} {t['status']}"
        introspection_str = ", ".join(t["introspection_source"])
        print(
            f"{t['id']:<25} | {t['tool_version']:<10} | {status_str:<12} | "
            f"{t['function_count']:<10} | {introspection_str:<15}"
        )

    return 0


def list_tools(*, json_output: bool, tool: str | None = None) -> int:
    """List installed tools and their status."""
    config = load_config()

    def _filter_tools(
        details: list[dict[str, Any]], filter_val: str | None
    ) -> list[dict[str, Any]]:
        if not filter_val:
            return details
        return [t for t in details if t["id"] == filter_val or t["id"] == f"tools.{filter_val}"]

    # Cache setup
    cache_dir = get_cli_cache_dir()
    envs_cache = InstalledEnvsCache(cache_dir)
    tools_cache = ListToolsCache(cache_dir)

    # 1. Environment manager check
    manager = detect_env_manager()
    manager_exe = manager[1] if manager else ""

    # 2. Try fast path with caches
    manifest_paths = discover_manifest_paths(config.tool_manifest_roots)
    installed_envs = None
    if manager_exe:
        installed_envs = envs_cache.get(manager_exe)

    if installed_envs is not None:
        # We have cached envs, check tools cache
        envs_hash = hashlib.sha256(json.dumps(sorted(list(installed_envs))).encode()).hexdigest()
        fingerprint = tools_cache.get_fingerprint(manifest_paths, envs_hash)
        cached_payload = tools_cache.get(fingerprint)
        if cached_payload is not None:
            filtered = _filter_tools(cached_payload, tool)
            return _render_list(filtered, json_output)

    # 3. Cache miss (either envs or tools)
    if installed_envs is None:
        if manager_exe:
            installed_envs = _get_installed_envs(manager_exe)
        else:
            installed_envs = set()

    # Update envs cache and get final hash
    envs_hash = envs_cache.put(manager_exe, installed_envs) if manager_exe else ""

    # Load manifests and build tool details
    manifests, _ = load_manifests(config.tool_manifest_roots)
    manifests.sort(key=lambda m: m.tool_id or "")

    tool_details: list[dict[str, Any]] = []
    for m in manifests:
        tool_id = m.tool_id or "unknown"
        env_id = m.env_id
        fn_count = len(m.functions)
        env_exists = env_id in installed_envs if env_id else False

        if env_exists:
            status = "installed"
            status_char = "✓"
        else:
            status = "partial"
            status_char = "⚠"

        sources = sorted({s for s in (fn.introspection_source for fn in m.functions) if s})

        tool_details.append(
            {
                "id": tool_id,
                "status": status,
                "status_char": status_char,
                "function_count": fn_count,
                "env_id": env_id,
                "tool_version": m.tool_version,
                "introspection_source": sources,
            }
        )

    # Update tools cache
    fingerprint = tools_cache.get_fingerprint(manifest_paths, envs_hash)
    tools_cache.put(fingerprint, tool_details)

    filtered = _filter_tools(tool_details, tool)
    return _render_list(filtered, json_output)
