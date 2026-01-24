from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from bioimage_mcp.bootstrap.configure import configure
from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.config.loader import find_repo_root

PROFILES = {
    "cpu": ["base", "cellpose"],  # Default CPU profile
    "gpu": ["base", "cellpose"],  # GPU adds CUDA post-install
    "minimal": ["base"],  # Just the base
}


def discover_available_tools() -> dict[str, Path]:
    """Return {tool_name: env_yaml_path} for all tools in envs/ directory."""
    repo_root = find_repo_root()
    base_dir = repo_root if repo_root else Path.cwd()
    envs_dir = base_dir / "envs"

    tools = {}
    if envs_dir.exists():
        for f in envs_dir.glob("bioimage-mcp-*.yaml"):
            # bioimage-mcp-cellpose.yaml -> cellpose
            tool_name = f.stem.replace("bioimage-mcp-", "")
            tools[tool_name] = f
    return tools


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


def _env_exists(exe: str, env_name: str) -> bool:
    """Check if a conda/micromamba environment exists."""
    try:
        proc = subprocess.run(
            [exe, "env", "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False

        output = proc.stdout
        json_start = output.find("{")
        if json_start == -1:
            return False

        data = json.loads(output[json_start:])
        envs = data.get("envs", [])
        for env in envs:
            if Path(env).name == env_name:
                return True
        return False
    except Exception:
        return False


def _lockfile_for_env(env_file: Path) -> Path:
    return env_file.with_suffix(".lock.yml")


def _install_env_with_lock(
    conda_lock_exe: str,
    env_name: str,
    lockfile: Path,
) -> bool:
    result = subprocess.run(
        [conda_lock_exe, "install", "-n", env_name, str(lockfile)],
        check=False,
    )
    return result.returncode == 0


def _collect_pip_deps(env_file: Path) -> list[str]:
    raw = yaml.safe_load(env_file.read_text())
    dependencies = raw.get("dependencies", []) if isinstance(raw, dict) else []
    pip_deps: list[str] = []
    for dep in dependencies:
        if isinstance(dep, dict) and "pip" in dep:
            pip_items = dep["pip"]
            if isinstance(pip_items, list):
                pip_deps.extend(pip_items)
    return pip_deps


def _normalize_pip_dep(dep: str, env_file: Path) -> str:
    if dep.startswith("-e "):
        rel_path = dep[3:].strip()
        abs_path = (env_file.parent / rel_path).resolve()
        return f"-e {abs_path}"
    return dep


def _install_pip_deps(exe: str, env_name: str, env_file: Path) -> bool:
    pip_deps = _collect_pip_deps(env_file)
    if not pip_deps:
        return True

    normalized = [_normalize_pip_dep(dep, env_file) for dep in pip_deps]
    cmd = [exe, "run", "-n", env_name, "python", "-m", "pip", "install", *normalized]
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _install_env(exe: str, manager: str, env_name: str, env_file: Path) -> bool:
    """Install or update a conda/micromamba environment."""
    # Try update first
    cmd = [exe, "env", "update", "-n", env_name, "-f", str(env_file)]
    if manager != "micromamba":
        cmd.append("--prune")

    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        return True

    # If update fails, try create
    if manager == "micromamba":
        create_cmd = [exe, "create", "-n", env_name, "-f", str(env_file), "-y"]
    else:
        create_cmd = [exe, "env", "create", "-n", env_name, "-f", str(env_file), "-y"]

    result = subprocess.run(create_cmd, check=False)
    return result.returncode == 0


def _gpu_post_install(exe: str, env_name: str) -> None:
    """Configure GPU support (specifically for cellpose/pytorch)."""
    print(f"Configuring GPU support for {env_name}...")
    subprocess.run(
        [exe, "remove", "-n", env_name, "-y", "cpuonly"],
        check=False,
    )
    subprocess.run(
        [
            exe,
            "install",
            "-n",
            env_name,
            "-y",
            "-c",
            "nvidia",
            "pytorch-cuda=11.8",
        ],
        check=False,
    )


def install(
    *,
    tools: list[str] | None = None,
    profile: str | None = None,
    force: bool = False,
) -> int:
    """Install/update the base and tool environments."""
    detected = detect_env_manager()
    if not detected:
        print("Error: No micromamba/conda/mamba found on PATH", file=sys.stderr)
        return 1

    manager, exe, _version = detected
    available_tools = discover_available_tools()

    # Resolve tool list
    if profile:
        if profile not in PROFILES:
            choices = ", ".join(PROFILES.keys())
            print(f"Error: Invalid profile '{profile}'. Choices: {choices}", file=sys.stderr)
            return 1
        tool_names = list(PROFILES[profile])
    elif tools:
        tool_names = list(tools)
    else:
        # Default to cpu profile
        profile = "cpu"
        tool_names = list(PROFILES[profile])

    # Always prepend "base" if not in list (base is required)
    if "base" not in tool_names:
        tool_names.insert(0, "base")

    # Validate tools exist
    for name in tool_names:
        if name not in available_tools:
            print(f"Error: Tool '{name}' not found in envs/ directory.", file=sys.stderr)
            return 1

    stats = {"installed": 0, "skipped": 0, "failed": 0}

    for name in tool_names:
        env_name = f"bioimage-mcp-{name}"
        env_file = available_tools[name]
        lockfile = _lockfile_for_env(env_file)
        conda_lock_exe = shutil.which("conda-lock")

        # Check if exists
        exists = _env_exists(exe, env_name)
        if exists and not force:
            print(f"{name} already installed (use --force to reinstall)")
            stats["skipped"] += 1
            continue

        print(f"Installing {name}...")

        # Install logic
        if conda_lock_exe and lockfile.exists():
            success = _install_env_with_lock(conda_lock_exe, env_name, lockfile)
        else:
            success = _install_env(exe, manager, env_name, env_file)
            if success:
                success = _install_pip_deps(exe, env_name, env_file)
        if not success:
            print(f"Failed to install {name}")
            stats["failed"] += 1
            continue

        # GPU post-install for cellpose
        if profile == "gpu" and name == "cellpose":
            _gpu_post_install(exe, env_name)

        stats["installed"] += 1

    summary = (
        f"\nSummary: Installed: {stats['installed']}, "
        f"Skipped: {stats['skipped']}, Failed: {stats['failed']}"
    )
    print(summary)

    if stats["failed"] == 0:
        _ensure_tool_manifest_roots()
        print("Next: run `bioimage-mcp doctor`")
        return 0
    return 1
