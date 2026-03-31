from __future__ import annotations

import subprocess
from pathlib import Path


def test_install_rejects_invalid_profile() -> None:
    """Test that install returns nonzero for invalid profile."""
    from bioimage_mcp.bootstrap.install import install

    result = install(profile="invalid")

    assert result != 0


def test_install_returns_error_when_no_env_manager(monkeypatch, capsys) -> None:
    """Test that install returns error when no env manager found."""
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: None,
    )

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="cpu")
    err = capsys.readouterr().err

    assert result != 0
    assert "No micromamba/conda/mamba found" in err


def test_install_returns_error_when_env_file_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that install returns error when env file is missing."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("mamba", "/usr/bin/mamba", "2.0"),
    )

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="cpu")
    err = capsys.readouterr().err

    assert result != 0
    assert "Tool 'base' not found" in err


def test_install_calls_env_manager_with_correct_args(tmp_path: Path, monkeypatch) -> None:
    """Test that install calls the environment manager with correct arguments."""
    # Create the env files
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: bioimage-mcp-base\n")
    cellpose_env = envs_dir / "bioimage-mcp-cellpose.yaml"
    cellpose_env.write_text("name: bioimage-mcp-cellpose\n")

    monkeypatch.chdir(tmp_path)

    called_commands = []

    def mock_run(cmd, **kwargs):
        called_commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda *_: False)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("mamba", "/usr/bin/mamba", "2.0"),
    )

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="cpu")

    assert result == 0
    assert len(called_commands) == 2
    for cmd in called_commands:
        assert cmd[0] == "/usr/bin/mamba"
        assert "env" in cmd
        assert "update" in cmd
        assert "--prune" in cmd
    assert any("bioimage-mcp-base" in cmd for cmd in called_commands)
    assert any("bioimage-mcp-cellpose" in cmd for cmd in called_commands)


def test_install_calls_micromamba_without_prune(tmp_path: Path, monkeypatch) -> None:
    """Test that install calls micromamba without the --prune flag."""
    # Create the env files
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: bioimage-mcp-base\n")
    cellpose_env = envs_dir / "bioimage-mcp-cellpose.yaml"
    cellpose_env.write_text("name: bioimage-mcp-cellpose\n")

    monkeypatch.chdir(tmp_path)

    called_commands = []

    def mock_run(cmd, **kwargs):
        called_commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda *_: False)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("micromamba", "/usr/bin/micromamba", "1.5.0"),
    )

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="gpu")

    assert result == 0
    assert len(called_commands) == 4
    for cmd in called_commands:
        assert cmd[0] == "/usr/bin/micromamba"
        assert "--prune" not in cmd
    assert any("bioimage-mcp-base" in cmd for cmd in called_commands)
    assert any("bioimage-mcp-cellpose" in cmd for cmd in called_commands)
    assert any("remove" in cmd and "cpuonly" in cmd for cmd in called_commands)
    assert any("install" in cmd and "pytorch-cuda=11.8" in cmd for cmd in called_commands)


def test_install_microsam_orchestration(tmp_path: Path, monkeypatch) -> None:
    """Test that install microsam triggers specialized post-install."""
    import json

    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    (envs_dir / "bioimage-mcp-base.yaml").write_text("name: base")
    (envs_dir / "bioimage-mcp-microsam.yaml").write_text("name: microsam")

    tools_dir = tmp_path / "tools" / "microsam" / "bioimage_mcp_microsam"
    tools_dir.mkdir(parents=True)
    script = tools_dir / "install_models.py"
    script.write_text("import json; print(json.dumps({'cache_path': '/tmp/models'}))")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("conda", "conda", "24.1.0"),
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda *_: False)

    called_commands = []

    def mock_run(cmd, **kwargs):
        called_commands.append(cmd)
        # Mock success for most, but specialize for sanity check and pip
        if "import micro_sam" in str(cmd):
            return subprocess.CompletedProcess(
                cmd, 0, stdout="micro_sam imported successfully", stderr=""
            )
        if "install_models.py" in str(cmd):
            return subprocess.CompletedProcess(
                cmd, 0, stdout=json.dumps({"cache_path": "/tmp/models"}), stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._ensure_tool_manifest_roots", lambda: None)

    from bioimage_mcp.bootstrap.install import install

    result = install(tools=["microsam"])

    assert result == 0
    # Check that microsam specific steps were called
    assert any(
        "pip" in cmd and any("trackastra" in part for part in cmd) for cmd in called_commands
    )
    assert any("pip" in cmd and any("MobileSAM" in part for part in cmd) for cmd in called_commands)
    assert any(any("install_models.py" in part for part in cmd) for cmd in called_commands)

    # Check state file
    state_file = tmp_path / ".bioimage-mcp" / "state" / "microsam_models.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["cache_path"] == "/tmp/models"


def test_install_microsam_skips_lockfile_path(tmp_path: Path, monkeypatch) -> None:
    """Microsam should install from the source spec, not conda-lock."""
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    microsam_env = envs_dir / "bioimage-mcp-microsam.yaml"
    microsam_env.write_text("name: microsam\n")
    microsam_lock = envs_dir / "bioimage-mcp-microsam.lock.yml"
    microsam_lock.write_text("version: 1\n")
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: base\n")
    base_lock = envs_dir / "bioimage-mcp-base.lock.yml"
    base_lock.write_text("version: 1\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("micromamba", "/usr/bin/micromamba", "1.5.0"),
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda *_: False)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._microsam_post_install", lambda *_: True)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._ensure_tool_manifest_roots", lambda: None)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install.shutil.which", lambda exe: exe)

    lock_calls: list[tuple[str, str, Path]] = []
    env_calls: list[tuple[str, str, str, Path]] = []

    def mock_install_with_lock(conda_lock_exe: str, env_name: str, lockfile: Path) -> bool:
        lock_calls.append((conda_lock_exe, env_name, lockfile))
        return True

    def mock_install_env(exe: str, manager: str, env_name: str, env_file: Path) -> bool:
        env_calls.append((exe, manager, env_name, env_file))
        return True

    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install._install_env_with_lock", mock_install_with_lock
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._install_env", mock_install_env)

    from bioimage_mcp.bootstrap.install import install

    result = install(tools=["microsam"])

    assert result == 0
    assert ("conda-lock", "bioimage-mcp-base", base_lock) in lock_calls
    assert ("conda-lock", "bioimage-mcp-microsam", microsam_lock) not in lock_calls
    assert ("/usr/bin/micromamba", "micromamba", "bioimage-mcp-microsam", microsam_env) in env_calls


def test_install_microsam_gpu_linux(tmp_path: Path, monkeypatch) -> None:
    """Test that install microsam --profile gpu triggers GPU setup on Linux."""
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    (envs_dir / "bioimage-mcp-base.yaml").write_text("name: base")
    (envs_dir / "bioimage-mcp-microsam.yaml").write_text("name: microsam")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("conda", "conda", "24.1.0"),
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda *_: False)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    # Mock _microsam_post_install to avoid complexity
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._microsam_post_install", lambda *_: True)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._ensure_tool_manifest_roots", lambda: None)

    called_commands = []

    def mock_run(cmd, **kwargs):
        called_commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    from bioimage_mcp.bootstrap.install import install

    result = install(tools=["microsam"], profile="gpu")

    assert result == 0
    assert any(any("pytorch-cuda=12.1" in str(elem) for elem in cmd) for cmd in called_commands)


def test_install_falls_back_to_env_file_when_lock_install_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Lockfile install failures should retry with the source env YAML."""
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: bioimage-mcp-base\n")
    base_lock = envs_dir / "bioimage-mcp-base.lock.yml"
    base_lock.write_text("version: 1\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("micromamba", "/usr/bin/micromamba", "1.5.0"),
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda *_: False)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._ensure_tool_manifest_roots", lambda: None)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install.shutil.which", lambda exe: exe)

    lock_calls: list[tuple[str, str, Path]] = []
    env_calls: list[tuple[str, str, str, Path]] = []

    def mock_install_with_lock(conda_lock_exe: str, env_name: str, lockfile: Path) -> bool:
        lock_calls.append((conda_lock_exe, env_name, lockfile))
        return False

    def mock_install_env(exe: str, manager: str, env_name: str, env_file: Path) -> bool:
        env_calls.append((exe, manager, env_name, env_file))
        return True

    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install._install_env_with_lock", mock_install_with_lock
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._install_env", mock_install_env)

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="minimal")
    out = capsys.readouterr().out

    assert result == 0
    assert lock_calls == [("conda-lock", "bioimage-mcp-base", base_lock)]
    assert env_calls == [("/usr/bin/micromamba", "micromamba", "bioimage-mcp-base", base_env)]
    assert "Lockfile install failed for base" in out


def test_install_falls_back_to_env_file_when_lock_install_does_not_create_env(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A successful lockfile install must still produce the named env."""
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: bioimage-mcp-base\n")
    base_lock = envs_dir / "bioimage-mcp-base.lock.yml"
    base_lock.write_text("version: 1\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("micromamba", "/usr/bin/micromamba", "1.5.0"),
    )
    env_exists_calls = iter([False, False])
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install._env_exists",
        lambda *_: next(env_exists_calls),
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._ensure_tool_manifest_roots", lambda: None)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install.shutil.which", lambda exe: exe)

    lock_calls: list[tuple[str, str, Path]] = []
    env_calls: list[tuple[str, str, str, Path]] = []

    def mock_install_with_lock(conda_lock_exe: str, env_name: str, lockfile: Path) -> bool:
        lock_calls.append((conda_lock_exe, env_name, lockfile))
        return True

    def mock_install_env(exe: str, manager: str, env_name: str, env_file: Path) -> bool:
        env_calls.append((exe, manager, env_name, env_file))
        return True

    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install._install_env_with_lock", mock_install_with_lock
    )
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._install_env", mock_install_env)

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="minimal")
    out = capsys.readouterr().out

    assert result == 0
    assert lock_calls == [("conda-lock", "bioimage-mcp-base", base_lock)]
    assert env_calls == [("/usr/bin/micromamba", "micromamba", "bioimage-mcp-base", base_env)]
    assert "did not create the expected environment for base" in out
