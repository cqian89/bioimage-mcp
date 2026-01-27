from __future__ import annotations

import json
import subprocess
from typing import Any

from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import load_manifests


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


def list_tools(*, json_output: bool) -> int:
    """List installed tools and their status."""
    config = load_config()
    manifests, _ = load_manifests(config.tool_manifest_roots)

    manager = detect_env_manager()
    installed_envs = set()
    if manager:
        installed_envs = _get_installed_envs(manager[1])

    tool_details: list[dict[str, Any]] = []
    # Sort manifests by tool_id for consistency
    manifests.sort(key=lambda m: m.tool_id or "")

    for m in manifests:
        tool_id = m.tool_id or "unknown"
        env_id = m.env_id
        fn_count = len(m.functions)
        env_exists = env_id in installed_envs if env_id else False

        # Status logic:
        # - "installed" if env exists
        # - "partial" if manifest exists but env missing
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
