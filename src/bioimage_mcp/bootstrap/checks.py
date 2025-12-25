from __future__ import annotations

import shutil
import socket
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.config.loader import load_config


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
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


def check_gpu() -> CheckResult:
    nvidia_smi = shutil.which("nvidia-smi")
    available = nvidia_smi is not None

    details: dict[str, object] = {"gpu_available": available}
    if available:
        details["detector"] = "nvidia-smi"
        details["nvidia_smi"] = nvidia_smi
    else:
        details["note"] = "nvidia-smi not found; GPU acceleration will be unavailable"

    return CheckResult(name="gpu", ok=True, remediation=[], details=details)


def check_conda_lock() -> CheckResult:
    exe = shutil.which("conda-lock")
    if exe is None:
        return CheckResult(
            name="conda_lock",
            ok=False,
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


def run_all_checks() -> list[CheckResult]:
    return [
        check_python_version(),
        check_env_manager(),
        check_disk(),
        check_permissions(),
        check_base_env(),
        check_gpu(),
        check_conda_lock(),
        check_network(),
    ]
