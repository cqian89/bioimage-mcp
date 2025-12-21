from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from bioimage_mcp.bootstrap.configure import configure
from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.config.loader import find_repo_root


def _ensure_tool_manifest_roots() -> None:
    config_dir = Path.cwd() / ".bioimage-mcp"
    config_path = config_dir / "config.yaml"

    if not config_path.exists():
        configure()

    data: dict = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text())
        if isinstance(loaded, dict):
            data = loaded

    roots = data.get("tool_manifest_roots", [])
    if not isinstance(roots, list):
        roots = []
    roots = [str(root) for root in roots]

    home_tools = str(Path.home() / ".bioimage-mcp" / "tools")
    if home_tools not in roots:
        roots.append(home_tools)

    repo_root = find_repo_root()
    if repo_root:
        tools_dir = repo_root / "tools"
        if tools_dir.exists():
            for tool_dir in tools_dir.iterdir():
                if tool_dir.is_dir() and (tool_dir / "manifest.yaml").exists():
                    path = str(tool_dir)
                    if path not in roots:
                        roots.append(path)

    data["tool_manifest_roots"] = roots
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False))


def install(*, profile: str) -> int:
    """Install/update the base and tool environments."""

    if profile not in {"cpu", "gpu"}:
        raise ValueError("profile must be cpu or gpu")

    detected = detect_env_manager()
    if not detected:
        raise RuntimeError("No micromamba/conda/mamba found on PATH")

    manager, exe, _version = detected

    env_specs = [
        ("bioimage-mcp-base", Path.cwd() / "envs" / "bioimage-mcp-base.yaml"),
        ("bioimage-mcp-cellpose", Path.cwd() / "envs" / "bioimage-mcp-cellpose.yaml"),
    ]

    for _env_name, env_file in env_specs:
        if not env_file.exists():
            raise FileNotFoundError(f"Missing env spec: {env_file}")

    for env_name, env_file in env_specs:
        cmd = [exe, "env", "update", "-n", env_name, "-f", str(env_file)]
        if manager != "micromamba":
            cmd.append("--prune")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            if manager == "micromamba":
                create_cmd = [exe, "create", "-n", env_name, "-f", str(env_file), "-y"]
            else:
                create_cmd = [exe, "env", "create", "-n", env_name, "-f", str(env_file), "-y"]
            subprocess.run(create_cmd, check=False)

    if profile == "gpu":
        subprocess.run(
            [exe, "remove", "-n", "bioimage-mcp-cellpose", "-y", "cpuonly"],
            check=False,
        )
        subprocess.run(
            [
                exe,
                "install",
                "-n",
                "bioimage-mcp-cellpose",
                "-y",
                "-c",
                "nvidia",
                "pytorch-cuda=11.8",
            ],
            check=False,
        )

    _ensure_tool_manifest_roots()

    print("Next: run `bioimage-mcp doctor`")
    return 0
