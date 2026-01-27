from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bioimage_mcp.bootstrap.env_manager import detect_env_manager, get_available_envs
from bioimage_mcp.config.loader import find_repo_root, load_config
from bioimage_mcp.registry.loader import load_manifest_file, load_manifests


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    required: bool = True
    remediation: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def check_python_version() -> CheckResult:
    ok = sys.version_info >= (3, 13)
    remediation = [] if ok else ["Install Python 3.13+ and ensure it's on PATH"]
    return CheckResult(
        name="python", ok=ok, remediation=remediation, details={"version": sys.version}
    )


def check_env_manager() -> CheckResult:
    detected = detect_env_manager()
    if not detected:
        return CheckResult(
            name="env_manager",
            ok=False,
            remediation=["Install micromamba (preferred) or conda/mamba"],
        )

    name, exe, version = detected
    return CheckResult(
        name="env_manager",
        ok=True,
        remediation=[],
        details={"manager": name, "executable": exe, "version": version},
    )


def check_disk(min_free_gb: float = 1.0) -> CheckResult:
    config = load_config()
    root = Path(config.artifact_store_root)
    # Find existing parent for disk_usage check (the path may not exist yet)
    check_path = root
    while not check_path.exists() and check_path.parent != check_path:
        check_path = check_path.parent
    try:
        usage = shutil.disk_usage(check_path)
        free_gb = usage.free / (1024**3)
        ok = free_gb >= min_free_gb
        remediation = (
            [] if ok else [f"Free at least {min_free_gb:.0f}GB on the artifact store volume"]
        )
        return CheckResult(
            name="disk", ok=ok, remediation=remediation, details={"free_gb": free_gb}
        )
    except OSError as exc:
        return CheckResult(
            name="disk",
            ok=False,
            remediation=["Unable to check disk space for artifact store"],
            details={"error": str(exc)},
        )


def check_permissions() -> CheckResult:
    config = load_config()
    root = Path(config.artifact_store_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".bioimage_mcp_write_test"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        return CheckResult(name="permissions", ok=True)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="permissions",
            ok=False,
            remediation=[f"Ensure write permissions to artifact_store_root: {root}"],
            details={"error": str(exc)},
        )


def check_base_env(env_name: str = "bioimage-mcp-base") -> CheckResult:
    detected = detect_env_manager()
    if not detected:
        return CheckResult(
            name="base_env",
            ok=False,
            remediation=["Install micromamba/conda, then run: bioimage-mcp install --profile cpu"],
        )

    # v0.0 heuristic: we can't reliably inspect all managers without invoking them.
    # Treat presence as sufficient for now; install will ensure the env exists.
    return CheckResult(
        name="base_env",
        ok=True,
        remediation=[],
        details={"env": env_name, "note": "validated by install step"},
    )


def check_tool_consolidation() -> CheckResult:
    repo_root = find_repo_root()
    if not repo_root:
        return CheckResult(
            name="tool_consolidation",
            ok=False,
            remediation=["Run checks from the bioimage-mcp repository"],
            details={"reason": "repo_root_not_found"},
        )

    errors: list[str] = []
    remediation: list[str] = []
    details: dict[str, object] = {"repo_root": str(repo_root)}

    env_spec = repo_root / "envs" / "bioimage-mcp-base.yaml"
    if not env_spec.exists():
        errors.append("missing_base_env_spec")
        remediation.append(f"Restore base env spec at {env_spec}")

    base_manifest_path = repo_root / "tools" / "base" / "manifest.yaml"
    if not base_manifest_path.exists():
        errors.append("missing_base_manifest")
        remediation.append(f"Restore base manifest at {base_manifest_path}")
    else:
        manifest, diag = load_manifest_file(base_manifest_path)
        if manifest is None or (diag is not None and diag.errors):
            errors.append("invalid_base_manifest")
            details["base_manifest_errors"] = (
                diag.errors if diag is not None else ["unknown manifest error"]
            )

    builtin_path = repo_root / "tools" / "builtin"
    if builtin_path.exists():
        errors.append("builtin_present")
        remediation.append("Remove tools/builtin to enforce unified base tool pack")
        details["builtin_path"] = str(builtin_path)

    if errors:
        details["errors"] = errors

    return CheckResult(
        name="tool_consolidation",
        ok=not errors,
        remediation=remediation,
        details=details,
    )


def check_gpu() -> CheckResult:
    # 1. Detect CUDA
    nvidia_smi_path = shutil.which("nvidia-smi")
    cuda_available = nvidia_smi_path is not None

    cuda_details: dict[str, object] = {"available": cuda_available}
    if cuda_available:
        cuda_details["detector"] = "nvidia-smi"
        cuda_details["nvidia_smi"] = nvidia_smi_path

        # Try to get additional info
        try:
            cmd = ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                parts = [p.strip() for p in proc.stdout.split(",")]
                if len(parts) >= 2:
                    cuda_details["model"] = parts[0]
                    cuda_details["memory"] = parts[1]
        except Exception:  # noqa: BLE001
            pass

    # 2. Detect MPS (Apple Silicon)
    mps_available = False
    is_darwin = platform.system() == "Darwin"
    if is_darwin:
        try:
            # Check for ARM64 (Apple Silicon)
            proc = subprocess.run(
                ["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True, check=False
            )
            if proc.returncode == 0 and proc.stdout.strip() == "1":
                mps_available = True
        except Exception:  # noqa: BLE001
            pass

    mps_details: dict[str, object] = {
        "available": mps_available,
        "detector": "sysctl" if is_darwin else None,
        "apple_silicon": is_darwin and mps_available,
    }

    details: dict[str, object] = {
        "gpu_available": cuda_available or mps_available,
        "cuda": cuda_details,
        "mps": mps_details,
    }

    if not (cuda_available or mps_available):
        details["note"] = "No GPU (CUDA or MPS) detected; GPU acceleration will be unavailable"

    return CheckResult(name="gpu", ok=True, remediation=[], details=details)


def check_conda_lock() -> CheckResult:
    exe = shutil.which("conda-lock")
    if exe is None:
        return CheckResult(
            name="conda_lock",
            ok=False,
            required=False,
            remediation=["Install conda-lock>=4.0.0 (used for reproducible env locks)"],
        )
    return CheckResult(name="conda_lock", ok=True, details={"executable": exe})


def check_network(host: str = "pypi.org", port: int = 443, timeout_s: float = 2.0) -> CheckResult:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return CheckResult(name="network", ok=True)
    except OSError as exc:
        return CheckResult(
            name="network",
            ok=False,
            remediation=[f"Check network connectivity (failed to connect to {host}:{port})"],
            details={"error": str(exc)},
        )


def check_tool_environments() -> CheckResult:
    config = load_config()
    try:
        manifests, _ = load_manifests(config.tool_manifest_roots)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="tool_environments",
            ok=False,
            remediation=["Check tool_manifest_roots in config"],
            details={"error": str(exc)},
        )

    required_envs = {m.env_id for m in manifests if m.env_id}
    if not required_envs:
        return CheckResult(name="tool_environments", ok=True, details={"count": 0})

    available_envs = set(get_available_envs())
    missing = required_envs - available_envs

    if not missing:
        return CheckResult(name="tool_environments", ok=True, details={"count": len(required_envs)})

    remediation = [f"Install missing environments: {', '.join(sorted(missing))}"]
    remediation.append("Run: bioimage-mcp install")

    return CheckResult(
        name="tool_environments",
        ok=False,
        remediation=remediation,
        details={"missing": sorted(list(missing)), "required": sorted(list(required_envs))},
    )


def run_all_checks() -> list[CheckResult]:
    return [
        check_python_version(),
        check_env_manager(),
        check_disk(),
        check_permissions(),
        check_base_env(),
        check_tool_environments(),
        check_tool_consolidation(),
        check_gpu(),
        check_conda_lock(),
        check_network(),
    ]
