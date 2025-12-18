from __future__ import annotations

from dataclasses import dataclass

from bioimage_mcp.bootstrap.checks import (
    check_base_env,
    check_conda_lock,
    check_disk,
    check_env_manager,
    check_gpu,
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
    result = check_gpu()
    assert result.ok is True
    assert result.details["gpu_available"] is False
    assert "note" in result.details


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


def test_run_all_checks_returns_eight_results(monkeypatch) -> None:
    # Avoid real network and disk.
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_network", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_disk", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_permissions", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_conda_lock", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_base_env", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_env_manager", lambda: check_gpu())
    monkeypatch.setattr("bioimage_mcp.bootstrap.checks.check_python_version", lambda: check_gpu())

    results = run_all_checks()
    assert len(results) == 8


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
