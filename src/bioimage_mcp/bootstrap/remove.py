from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from bioimage_mcp.bootstrap.env_manager import detect_env_manager


def is_tool_active(tool_name: str) -> bool:
    """Check if tool has an active worker process."""
    env_id = f"bioimage-mcp-{tool_name}"

    try:
        # Check if any process has the env_id in its cmdline
        # pgrep -f is available on most linux/mac systems
        proc = subprocess.run(
            ["pgrep", "-f", env_id],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return True
    except Exception:  # noqa: BLE001
        # On error/uncertainty, return False (allow removal)
        pass

    return False


def _env_exists(exe: str, env_name: str) -> bool:
    """Check if a conda/micromamba environment exists."""
    try:
        proc = subprocess.run(
            [exe, "env", "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            envs = data.get("envs", [])
            for env in envs:
                if Path(env).name == env_name:
                    return True
            return False

        # Fallback to plain text if --json fails
        proc = subprocess.run(
            [exe, "env", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        return env_name in proc.stdout
    except Exception:  # noqa: BLE001
        return False


def remove_tool(tool_name: str, *, yes: bool = False) -> int:
    """Remove a tool environment.

    Args:
        tool_name: Tool to remove (e.g., 'cellpose')
        yes: Skip confirmation prompt

    Returns:
        0 on success, 1 on error
    """
    if tool_name == "base":
        print("Error: The 'base' environment cannot be removed.", file=sys.stderr)
        return 1

    detected = detect_env_manager()
    if not detected:
        print(
            "Error: No conda-like environment manager (micromamba, mamba, conda) found.",
            file=sys.stderr,
        )
        return 1

    _manager, exe, _version = detected
    env_id = f"bioimage-mcp-{tool_name}"

    # Check if env exists
    if not _env_exists(exe, env_id):
        print(
            f"Error: Tool '{tool_name}' is not installed (environment '{env_id}' not found).",
            file=sys.stderr,
        )
        return 1

    # Check if active
    if is_tool_active(tool_name):
        print(
            f"Error: Cannot remove {tool_name}: tool is currently running. Stop the server first.",
            file=sys.stderr,
        )
        return 1

    # Confirmation
    if not yes:
        try:
            ans = input(f"Remove {tool_name}? This will delete the conda environment. (y/N): ")
            if ans.lower() not in ("y", "yes"):
                print("Cancelled")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled")
            return 0

    # Execute removal
    print(f"Removing {tool_name} environment ({env_id})...")
    try:
        cmd = [exe, "env", "remove", "-n", env_id, "-y"]
        proc = subprocess.run(cmd, check=False)
        if proc.returncode == 0:
            print(f"Successfully removed {tool_name}")
            return 0

        print(f"Error: Failed to remove {tool_name} (exit code {proc.returncode})", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error executing removal: {exc}", file=sys.stderr)
        return 1
