from __future__ import annotations

import json
import sqlite3
import subprocess
from typing import Any

from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.config.loader import load_config


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
    db_path = config.artifact_store_root / "registry.db"

    if not db_path.exists():
        if json_output:
            print(json.dumps({"tools": []}))
        else:
            print(
                "No tools registered. Run 'bioimage-mcp install' "
                "or start the server to index tools."
            )

        return 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Fetch tools directly from DB for the status report
        rows = conn.execute(
            "SELECT tool_id, env_id, installed FROM tools ORDER BY tool_id"
        ).fetchall()

        manager = detect_env_manager()
        installed_envs = set()
        if manager:
            installed_envs = _get_installed_envs(manager[1])

        tool_details: list[dict[str, Any]] = []
        for row in rows:
            tool_id = row["tool_id"]
            env_id = row["env_id"]
            db_installed = bool(row["installed"])

            # Function count
            fn_row = conn.execute(
                "SELECT COUNT(*) as count FROM functions WHERE tool_id = ?", (tool_id,)
            ).fetchone()
            fn_count = fn_row["count"] if fn_row else 0

            env_exists = env_id in installed_envs if env_id else False

            # Status logic:
            # - "installed" if env exists and manifest valid (db says installed)
            # - "partial" if manifest exists but env missing
            # - "unavailable" if neither
            if env_exists and db_installed:
                status = "installed"
                status_char = "✓"
            elif db_installed:
                status = "partial"
                status_char = "⚠"
            else:
                status = "unavailable"
                status_char = "✗"

            tool_details.append(
                {
                    "id": tool_id,
                    "status": status,
                    "status_char": status_char,
                    "function_count": fn_count,
                    "env_id": env_id,
                }
            )

        if json_output:
            print(json.dumps({"tools": tool_details}))
            return 0

        if not tool_details:
            print("No tools found in registry.")
            return 0

        print(f"{'Tool':<30} | {'Status':<12} | {'Functions':<10}")
        print("-" * 60)
        for t in tool_details:
            status_str = f"{t['status_char']} {t['status']}"
            print(f"{t['id']:<30} | {status_str:<12} | {t['function_count']:<10}")

        return 0
    finally:
        conn.close()
