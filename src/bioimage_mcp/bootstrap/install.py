from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
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


def _install_env_from_spec(exe: str, manager: str, env_name: str, env_file: Path) -> bool:
    """Install an env from its source spec and then apply any pip-only deps."""
    success = _install_env(exe, manager, env_name, env_file)
    if success:
        success = _install_pip_deps(exe, env_name, env_file)
    return success


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

    # Install one-by-one to avoid pip resolver trying to replace conda packages
    # (notably numpy) when many packages are installed together.
    normalized = [_normalize_pip_dep(dep, env_file) for dep in pip_deps]
    for dep in normalized:
        pip_args: list[str] = ["python", "-m", "pip", "install"]
        if dep.startswith("-e "):
            pip_args.extend(["-e", dep[3:].strip()])
        else:
            pip_args.append(dep)
        cmd = [exe, "run", "-n", env_name, *pip_args]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(
                f"pip install failed for '{dep}' in {env_name} (exit {result.returncode})",
                file=sys.stderr,
            )
            if result.stdout:
                print(result.stdout, file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return False
    return True


def _install_env(exe: str, manager: str, env_name: str, env_file: Path) -> bool:
    """Install or update a conda/micromamba environment."""
    # If the env spec contains a pip section, strip it for the conda solve step.
    # We'll install pip deps separately via _install_pip_deps.
    raw = yaml.safe_load(env_file.read_text())
    dependencies = raw.get("dependencies", []) if isinstance(raw, dict) else []
    has_pip_section = any(isinstance(dep, dict) and "pip" in dep for dep in dependencies)
    env_file_for_conda = env_file

    tmp_dir_ctx = None
    if has_pip_section and isinstance(raw, dict) and isinstance(dependencies, list):
        stripped = dict(raw)
        stripped["dependencies"] = [
            dep for dep in dependencies if not (isinstance(dep, dict) and "pip" in dep)
        ]
        tmp_dir_ctx = tempfile.TemporaryDirectory(prefix="bioimage-mcp-env-")
        tmp_dir = Path(tmp_dir_ctx.name)
        env_file_for_conda = tmp_dir / env_file.name
        env_file_for_conda.write_text(yaml.safe_dump(stripped, sort_keys=False))

    # Try update first
    cmd = [exe, "env", "update", "-n", env_name, "-f", str(env_file_for_conda)]
    if manager != "micromamba":
        cmd.append("--prune")

    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        if tmp_dir_ctx is not None:
            tmp_dir_ctx.cleanup()
        return True

    # If update fails, try create
    if manager == "micromamba":
        create_cmd = [exe, "create", "-n", env_name, "-f", str(env_file_for_conda), "-y"]
    else:
        create_cmd = [exe, "env", "create", "-n", env_name, "-f", str(env_file_for_conda), "-y"]

    result = subprocess.run(create_cmd, check=False)
    if tmp_dir_ctx is not None:
        tmp_dir_ctx.cleanup()
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


def _microsam_gpu_post_install(exe: str, env_name: str) -> bool:
    """Configure GPU support for microsam."""
    import platform

    system = platform.system()
    machine = platform.machine()

    if system == "Linux":
        print(f"Configuring GPU support (CUDA) for {env_name}...")
        subprocess.run([exe, "remove", "-n", env_name, "-y", "cpuonly"], check=False)
        res = subprocess.run(
            [
                exe,
                "install",
                "-n",
                env_name,
                "-y",
                "-c",
                "pytorch",
                "-c",
                "nvidia",
                "pytorch::pytorch",
                "pytorch::torchvision",
                "pytorch::torchaudio",
                "pytorch::pytorch-cuda=12.1",
            ],
            check=False,
        )
        return res.returncode == 0
    elif system == "Darwin":
        if machine == "arm64":
            print(f"Using MPS on Apple Silicon for {env_name} (no additional steps needed).")
            return True
        else:
            print(
                f"Warning: GPU profile requested on Intel Mac for {env_name}. Falling back to CPU.",
                file=sys.stderr,
            )
            return True
    elif system == "Windows":
        print(f"GPU profile on Windows is best-effort for {env_name}.")
        res = subprocess.run(
            [
                exe,
                "install",
                "-n",
                env_name,
                "-y",
                "-c",
                "nvidia",
                "-c",
                "pytorch",
                "pytorch-cuda=12.1",
            ],
            check=False,
        )
        if res.returncode != 0:
            print(
                "GPU install failed on Windows. Recommend using WSL2, Linux, or macOS.",
                file=sys.stderr,
            )
        return True
    return True


def _microsam_post_install(exe: str, env_name: str) -> bool:
    """Run post-install steps for microsam (sanity, pip deps, models)."""
    print(f"Finalizing microsam installation in {env_name}...")

    # 1. Sanity import
    cmd = [
        exe,
        "run",
        "-n",
        env_name,
        "python",
        "-c",
        "import micro_sam; print('micro_sam imported successfully')",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Sanity check failed for {env_name}: {result.stderr}", file=sys.stderr)
        return False

    # 2. Install pip-only dependencies
    pip_deps = ["trackastra", "git+https://github.com/ChaoningZhang/MobileSAM.git"]
    for dep in pip_deps:
        cmd = [exe, "run", "-n", env_name, "python", "-m", "pip", "install", dep]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Failed to install pip dependency {dep}: {result.stderr}", file=sys.stderr)
            return False

    # 3. Model bootstrap
    repo_root = find_repo_root()
    script_path = repo_root / "tools" / "microsam" / "bioimage_mcp_microsam" / "install_models.py"
    if not script_path.exists():
        print(f"Model bootstrap script not found at {script_path}", file=sys.stderr)
        return False

    cmd = [exe, "run", "-n", env_name, "python", "-u", str(script_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=None, text=True, check=False)
    if result.returncode != 0:
        print(f"Model bootstrap failed for {env_name} (see output above)", file=sys.stderr)
        print(
            f"Remediation: Ensure network access and run: "
            f"{exe} run -n {env_name} python {script_path}",
            file=sys.stderr,
        )
        return False

    # 4. Capture JSON output and persist
    try:
        # Script is expected to output JSON to stdout
        output_data = json.loads(result.stdout)
        state_dir = Path.cwd() / ".bioimage-mcp" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "microsam_models.json").write_text(json.dumps(output_data, indent=2))

        cache_path = output_data.get("cache_path", "unknown")
        print(f"SUCCESS: microsam environment '{env_name}' ready. Models cached at: {cache_path}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Failed to parse model bootstrap output: {e}", file=sys.stderr)
        if result.stdout:
            print(f"Raw output: {result.stdout}")

    return True


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
    if tools == ["microsam"]:
        tool_names = ["microsam"]
        profile = profile or "cpu"
    elif profile:
        if profile not in PROFILES:
            choices = ", ".join(PROFILES.keys())
            print(f"Error: Invalid profile '{profile}'. Choices: {choices}", file=sys.stderr)
            return 1
        tool_names = list(PROFILES[profile])
    elif tools:
        tool_names = list(tools)
        # Default profile to cpu if not specified and microsam is present
        if not profile and "microsam" in tool_names:
            profile = "cpu"
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
            print(f"{name} already installed; updating")
        else:
            print(f"Installing {name}...")

        pip_deps = _collect_pip_deps(env_file)

        # Install logic
        # Note: conda-lock pip integration can be brittle; for envs with pip deps we
        # install conda deps first (without pip) then install pip deps separately.
        # Microsam always uses the separate flow for extra pip deps + models.
        if conda_lock_exe and lockfile.exists() and (not pip_deps or name == "microsam"):
            success = _install_env_with_lock(conda_lock_exe, env_name, lockfile)
            if not success:
                print(f"Lockfile install failed for {name}; retrying from {env_file.name}...")
                success = _install_env_from_spec(exe, manager, env_name, env_file)
            elif not _env_exists(exe, env_name):
                print(
                    f"Lockfile install did not create the expected environment for {name}; "
                    f"retrying from {env_file.name}..."
                )
                success = _install_env_from_spec(exe, manager, env_name, env_file)
        else:
            success = _install_env_from_spec(exe, manager, env_name, env_file)
        if not success:
            print(f"Failed to install {name}")
            stats["failed"] += 1
            continue

        # Tool-specific post-install steps
        if profile == "gpu" and name == "cellpose":
            _gpu_post_install(exe, env_name)

        if name == "microsam":
            if profile == "gpu":
                if not _microsam_gpu_post_install(exe, env_name):
                    print(f"Failed to configure GPU for {name}")
                    stats["failed"] += 1
                    continue
            if not _microsam_post_install(exe, env_name):
                stats["failed"] += 1
                continue

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
