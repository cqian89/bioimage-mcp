from __future__ import annotations

import subprocess
from pathlib import Path

from bioimage_mcp.bootstrap.env_manager import detect_env_manager


def install(*, profile: str) -> int:
    """Install/update the base environment used by built-in tools."""

    if profile not in {"cpu", "gpu"}:
        raise ValueError("profile must be cpu or gpu")

    detected = detect_env_manager()
    if not detected:
        raise RuntimeError("No micromamba/conda/mamba found on PATH")

    manager, exe, _version = detected

    env_file = Path.cwd() / "envs" / "bioimage-mcp-base.yaml"
    if not env_file.exists():
        raise FileNotFoundError(f"Missing env spec: {env_file}")

    cmd = [exe, "env", "update", "-n", "bioimage-mcp-base", "-f", str(env_file), "--prune"]
    if manager == "micromamba":
        cmd = [exe, "env", "update", "-n", "bioimage-mcp-base", "-f", str(env_file)]

    subprocess.run(cmd, check=False)

    print("Next: run `bioimage-mcp doctor`")
    return 0
