from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from bioimage_mcp.bootstrap.checks import (
    check_base_env,
    check_conda_lock,
    check_disk,
    check_env_manager,
    check_gpu,
    check_microsam_models,
    check_network,
    check_permissions,
    check_python_version,
    run_all_checks,
)
from bioimage_mcp.config.schema import Config


@dataclass(frozen=True)
class _DiskUsage:
    total: int
    used: int
    free: int


def test_check_python_version_passes_for_313_plus(monkeypatch) -> None:
    monkeypatch.setattr("sys.version_info", (3, 13, 0))
    result = check_python_version()
    assert result.ok is True


def test_check_python_version_fails_for_old_python(monkeypatch) -> None:
    monkeypatch.setattr("sys.version_info", (3, 12, 9))
    result = check_python_version()
    assert result.ok is False
    assert result.remediation


def test_check_env_manager_reports_selected_manager(monkeypatch) -> None:
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.detect_env_manager",
        lambda: ("micromamba", "/bin/micromamba", "1.0.0"),
    )
    result = check_env_manager()
    assert result.ok is True
    assert result.details["manager"] == "micromamba"


def test_check_disk_uses_threshold(monkeypatch, tmp_path) -> None:
    config = Config(
        artifact_store_root=tmp_path,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.load_config", lambda: config)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.shutil.disk_usage",
        lambda _p: _DiskUsage(total=10, used=9, free=0),
    )

    result = check_disk(min_free_gb=1)
    assert result.ok is False
    assert result.remediation


def test_check_permissions_can_write_artifact_root(monkeypatch, tmp_path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.load_config", lambda: config)

    result = check_permissions()
    assert result.ok is True


def test_check_base_env_requires_manager(monkeypatch) -> None:
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.detect_env_manager", lambda: None)
    result = check_base_env()
    assert result.ok is False


def test_check_gpu_is_graceful(monkeypatch) -> None:
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.shutil.which", lambda _n: None)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    result = check_gpu()
    assert result.ok is True
    assert result.details["gpu_available"] is False
    assert "note" in result.details


def test_check_gpu_mps_detection_on_apple_silicon(monkeypatch) -> None:
    # Mock no nvidia-smi
    monkeypatch.setattr("shutil.which", lambda _n: None)
    # Mock Darwin
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    # Mock subprocess.run for sysctl
    def mock_run(cmd, **kwargs):
        if cmd == ["sysctl", "-n", "hw.optional.arm64"]:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="1")
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr("subprocess.run", mock_run)

    result = check_gpu()
    assert result.ok is True
    assert result.details["gpu_available"] is True
    assert result.details["mps"]["available"] is True
    assert result.details["mps"]["apple_silicon"] is True
    assert result.details["cuda"]["available"] is False


def test_check_gpu_mps_not_available_on_linux(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _n: None)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    result = check_gpu()
    assert result.details["mps"]["available"] is False


def test_check_gpu_cuda_and_mps_both_detected(monkeypatch) -> None:
    # Mock nvidia-smi present
    monkeypatch.setattr(
        "shutil.which", lambda _n: "/usr/bin/nvidia-smi" if _n == "nvidia-smi" else None
    )
    # Mock Darwin
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    # Mock subprocess.run
    def mock_run(cmd, **kwargs):
        if cmd == ["sysctl", "-n", "hw.optional.arm64"]:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="1")
        if "nvidia-smi" in cmd[0]:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="NVIDIA A100, 40GB")
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr("subprocess.run", mock_run)

    result = check_gpu()
    assert result.details["gpu_available"] is True
    assert result.details["cuda"]["available"] is True
    assert result.details["mps"]["available"] is True
    assert result.details["cuda"]["model"] == "NVIDIA A100"


def test_check_gpu_nvidia_smi_query_failure_graceful(monkeypatch) -> None:
    monkeypatch.setattr(
        "shutil.which", lambda _n: "/usr/bin/nvidia-smi" if _n == "nvidia-smi" else None
    )

    # Mock nvidia-smi query failure
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr("subprocess.run", mock_run)

    result = check_gpu()
    assert result.details["cuda"]["available"] is True
    assert "model" not in result.details["cuda"]


def test_check_conda_lock_missing_fails(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _n: None)
    result = check_conda_lock()
    assert result.ok is False
    assert result.remediation


def test_check_network_failure_returns_remediation(monkeypatch) -> None:
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.socket.create_connection",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("nope")),
    )
    result = check_network(host="example.com")
    assert result.ok is False
    assert result.remediation


def test_run_all_checks_returns_results(monkeypatch) -> None:
    # Avoid real network and disk.
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_network", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_disk", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_permissions", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_conda_lock", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_base_env", lambda: check_gpu())
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.check_tool_consolidation", lambda: check_gpu()
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_env_manager", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_python_version", lambda: check_gpu())
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.check_tool_environments", lambda: check_gpu()
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_microsam_models", lambda: check_gpu())

    results = run_all_checks()
    assert len(results) == 11


def test_check_network_passes_when_socket_connects(monkeypatch) -> None:
    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.socket.create_connection", lambda *_a, **_kw: _Conn()
    )
    assert check_network().ok is True


def test_check_microsam_models_passes_when_record_exists(monkeypatch, tmp_path) -> None:
    # Set CWD to tmp_path
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".bioimage-mcp" / "state"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "microsam_models.json"

    # Mock models
    m1 = tmp_path / "vit_b"
    m1.touch()
    m2 = tmp_path / "vit_b_lm"
    m2.touch()
    m3 = tmp_path / "vit_b_em_organelles"
    m3.touch()

    state_file.write_text(
        json.dumps(
            {
                "ok": True,
                "models": {"vit_b": str(m1), "vit_b_lm": str(m2), "vit_b_em_organelles": str(m3)},
            }
        )
    )

    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.get_available_envs", lambda: ["bioimage-mcp-microsam"]
    )

    result = check_microsam_models()
    assert result.ok is True


def test_check_microsam_models_fails_when_record_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.get_available_envs", lambda: ["bioimage-mcp-microsam"]
    )

    result = check_microsam_models()
    assert result.ok is False
    assert "missing" in result.remediation[0].lower()


def test_check_microsam_models_fails_when_files_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".bioimage-mcp" / "state"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "microsam_models.json"

    state_file.write_text(
        json.dumps(
            {
                "ok": True,
                "models": {
                    "vit_b": str(tmp_path / "missing_vit_b"),
                    "vit_b_lm": str(tmp_path / "missing_vit_b_lm"),
                    "vit_b_em_organelles": str(tmp_path / "missing_vit_b_em_organelles"),
                },
            }
        )
    )

    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.checks.get_available_envs", lambda: ["bioimage-mcp-microsam"]
    )

    result = check_microsam_models()
    assert result.ok is False
    assert result.details["corrupt"]
