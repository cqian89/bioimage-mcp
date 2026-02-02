from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.bootstrap.list_cache import (
    InstalledEnvsCache,
    ListToolsCache,
    get_cli_cache_dir,
)
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import discover_manifest_paths, load_manifests


PACKAGE_TO_CONDA = {
    "scipy": "scipy",
    "phasorpy": "phasorpy",
    "skimage": "scikit-image",
    "pandas": "pandas",
    "xarray": "xarray",
    "cellpose": "cellpose",
    "trackpy": "trackpy",
    "stardist": "stardist",
    "tttrlib": "tttrlib",
}


def _get_conda_platform() -> str | None:
    plt = sys.platform
    arch = platform.machine().lower()
    if plt == "linux":
        return "linux-64" if arch == "x86_64" else "linux-aarch64"
    elif plt == "darwin":
        return "osx-arm64" if arch == "arm64" else "osx-64"
    elif plt == "win32":
        return "win-64"
    return None


def _resolve_version(env_id: str | None, package_id: str, manager_exe: str) -> str | None:
    if not env_id:
        return None

    conda_name = PACKAGE_TO_CONDA.get(package_id)
    if not conda_name:
        return None

    # 1. Lockfile resolution
    lock_path = Path("envs") / f"{env_id}.lock.yml"
    if lock_path.exists():
        try:
            with open(lock_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            current_plt = _get_conda_platform()
            packages = data.get("package", [])

            # First pass: try to match platform
            for pkg in packages:
                if pkg.get("name") == conda_name:
                    if current_plt and pkg.get("platform") == current_plt:
                        return str(pkg.get("version"))

            # Second pass: just return first match if platform didn't match or current_plt unknown
            for pkg in packages:
                if pkg.get("name") == conda_name:
                    return str(pkg.get("version"))
        except Exception:
            pass

    # 2. Live query resolution
    if manager_exe:
        try:
            proc = subprocess.run(
                [manager_exe, "list", "-n", env_id, "--json", conda_name],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                if isinstance(data, list):
                    for pkg in data:
                        if pkg.get("name") == conda_name:
                            return str(pkg.get("version"))
        except Exception:
            pass

    return None


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
        # Filter out internal metadata for JSON output to match schema
        json_payload = []
        for t in tool_details:
            json_payload.append(
                {
                    "id": t["id"],
                    "tool_version": t["tool_version"],
                    "library_version": t["library_version"],
                    "status": t["status"],
                    "function_count": t["function_count"],
                    "packages": t["packages"],
                }
            )
        print(json.dumps({"tools": json_payload}))
        return 0

    if not tool_details:
        print("No tools found in registry.")
        return 0

    print(f"{'Tool':<25} | {'Version':<10} | {'Status':<12} | {'Functions'}")
    print("-" * 65)
    for i, t in enumerate(tool_details):
        if i > 0:
            print()

        pkg_summary = ""
        if t["packages"]:
            pkg_list = [f"{p['id']}:{p['function_count']}" for p in t["packages"][:3]]
            pkg_summary = f" ({', '.join(pkg_list)}"
            if len(t["packages"]) > 3:
                pkg_summary += ", ..."
            pkg_summary += ")"

        functions_str = f"{t['function_count']}{pkg_summary}"
        version = t["library_version"] or t["tool_version"]
        print(f"{t['id']:<25} | {version:<10} | {t['status']:<12} | {functions_str}")

        # Render package rows
        for j, pkg in enumerate(t["packages"]):
            is_last = j == len(t["packages"]) - 1
            prefix = "  └── " if is_last else "  ├── "
            pkg_version = pkg["library_version"] or ""
            print(
                f"{prefix + pkg['id']:<25} | {pkg_version:<10} | {'':<12} | {pkg['function_count']}"
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
        return [t for t in details if t["id"] == filter_val or f"tools.{t['id']}" == filter_val]

    # Cache setup
    cache_dir = get_cli_cache_dir()
    envs_cache = InstalledEnvsCache(cache_dir)
    tools_cache = ListToolsCache(cache_dir)

    # 1. Environment manager check
    manager = detect_env_manager()
    manager_exe = manager[1] if manager else ""

    # 2. Try fast path with caches
    manifest_paths = discover_manifest_paths(config.tool_manifest_roots)
    lockfile_paths = list(Path("envs").glob("*.lock.yml"))
    installed_envs = None
    if manager_exe:
        installed_envs = envs_cache.get(manager_exe)

    if installed_envs is not None:
        # We have cached envs, check tools cache
        envs_hash = hashlib.sha256(json.dumps(sorted(list(installed_envs))).encode()).hexdigest()
        fingerprint = tools_cache.get_fingerprint(manifest_paths, envs_hash, lockfile_paths)
        cached_payload = tools_cache.get(fingerprint)
        if cached_payload is not None:
            # Check if all required dynamic caches exist
            missing_dynamic = False
            for t in cached_payload:
                if any("dynamic_discovery" in s for s in t.get("introspection_source", [])):
                    tool_id = t["id"]
                    full_tool_id = t.get("tool_id_full") or t.get("full_tool_id")
                    candidates = [tool_id]
                    if full_tool_id:
                        candidates.append(full_tool_id)
                    if not tool_id.startswith("tools."):
                        candidates.append(f"tools.{tool_id}")

                    dynamic_cache_exists = False
                    for cache_id in candidates:
                        dynamic_cache = (
                            Path.home()
                            / ".bioimage-mcp"
                            / "cache"
                            / "dynamic"
                            / cache_id
                            / "introspection_cache.json"
                        )
                        if dynamic_cache.exists():
                            dynamic_cache_exists = True
                            break

                    if not dynamic_cache_exists:
                        missing_dynamic = True
                        break

            if not missing_dynamic:
                filtered = _filter_tools(cached_payload, tool)
                return _render_list(filtered, json_output)
            else:
                # Invalidate if dynamic cache is missing so we fall through to discovery
                cached_payload = None

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
        full_tool_id = m.tool_id or "unknown"
        tool_id = full_tool_id.removeprefix("tools.")
        env_id = m.env_id
        fn_count = len(m.functions)
        env_exists = env_id in installed_envs if env_id else False

        status = "installed" if env_exists else "partial"

        # Resolve versions
        # For tools with primary library (e.g. cellpose), tool.library_version = resolved version
        # For base, it might be None if multiple libs.
        tool_lib_version = _resolve_version(env_id, tool_id, manager_exe)
        if tool_id == "base" and env_id:
            tool_lib_version = None

        packages = []
        if tool_id == "base":
            pkg_counts: dict[str, int] = {}
            for fn in m.functions:
                fn_id = fn.fn_id
                remainder = fn_id
                if fn_id.startswith(f"{tool_id}."):
                    remainder = fn_id[len(tool_id) + 1 :]

                if "." in remainder:
                    pkg_id = remainder.split(".")[0]
                else:
                    pkg_id = "root"
                pkg_counts[pkg_id] = pkg_counts.get(pkg_id, 0) + 1

            for pid, count in sorted(pkg_counts.items()):
                pkg_lib_version = _resolve_version(env_id, pid, manager_exe)
                packages.append(
                    {"id": pid, "library_version": pkg_lib_version, "function_count": count}
                )

        sources = sorted({s for s in (fn.introspection_source for fn in m.functions) if s})

        tool_details.append(
            {
                "id": tool_id,
                "tool_id_full": full_tool_id,
                "tool_version": m.tool_version,
                "library_version": tool_lib_version,
                "status": status,
                "function_count": fn_count,
                "packages": packages,
                "env_id": env_id,
                "introspection_source": sources,
            }
        )

    # Update tools cache
    fingerprint = tools_cache.get_fingerprint(manifest_paths, envs_hash, lockfile_paths)
    tools_cache.put(fingerprint, tool_details)

    filtered = _filter_tools(tool_details, tool)
    return _render_list(filtered, json_output)
