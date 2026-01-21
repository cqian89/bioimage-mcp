from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.smoke.utils.native_executor import (
    EnvironmentNotFoundError,
    NativeExecutor,
    NativeExecutorError,
)


@pytest.mark.smoke_minimal
def test_native_executor_init_auto_detect():
    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda x: "/usr/bin/conda" if x == "conda" else None
        executor = NativeExecutor()
        assert executor.conda_path == "/usr/bin/conda"


@pytest.mark.smoke_minimal
def test_native_executor_init_explicit():
    executor = NativeExecutor(conda_path="/custom/conda")
    assert executor.conda_path == "/custom/conda"


@pytest.mark.smoke_minimal
def test_native_executor_env_exists():
    executor = NativeExecutor(conda_path="conda")
    with patch("subprocess.check_output") as mock_check_output:
        # Mock conda env list output
        mock_check_output.return_value = (
            b"base /home/user/anaconda3\ntest_env /home/user/anaconda3/envs/test_env"
        )
        assert executor.env_exists("test_env") is True
        assert executor.env_exists("non_existent") is False


@pytest.mark.smoke_minimal
def test_native_executor_run_script_success(tmp_path):
    executor = NativeExecutor(conda_path="conda")
    script = tmp_path / "script.py"
    script.write_text("import json; print(json.dumps({'status': 'ok'}))")

    with patch.object(NativeExecutor, "env_exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = '{"status": "ok"}'
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            result = executor.run_script("test_env", script, ["--arg1"])
            assert result == {"status": "ok"}

            # Verify call args
            args, _ = mock_run.call_args
            cmd = args[0]
            assert cmd[0] == "conda"
            assert "run" in cmd
            assert "-n" in cmd
            assert "test_env" in cmd
            assert "python" in cmd
            assert str(script) in cmd
            assert "--arg1" in cmd


@pytest.mark.smoke_minimal
def test_native_executor_run_script_env_missing():
    executor = NativeExecutor(conda_path="conda")
    with patch.object(NativeExecutor, "env_exists", return_value=False):
        with pytest.raises(EnvironmentNotFoundError):
            executor.run_script("missing_env", Path("script.py"), [])


@pytest.mark.smoke_minimal
def test_native_executor_run_script_json_error(tmp_path):
    executor = NativeExecutor(conda_path="conda")
    script = tmp_path / "script.py"

    with patch.object(NativeExecutor, "env_exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "not json"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with pytest.raises(NativeExecutorError, match="Failed to parse JSON output"):
                executor.run_script("test_env", script, [])


@pytest.mark.smoke_minimal
def test_native_executor_run_script_timeout(tmp_path):
    executor = NativeExecutor(conda_path="conda")
    script = tmp_path / "script.py"

    with patch.object(NativeExecutor, "env_exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

            with pytest.raises(TimeoutError):
                executor.run_script("test_env", script, [], timeout=1)


@pytest.mark.smoke_minimal
def test_native_executor_run_script_nonzero_exit(tmp_path):
    executor = NativeExecutor(conda_path="conda")
    script = tmp_path / "script.py"

    with patch.object(NativeExecutor, "env_exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "some error"
            mock_run.return_value = mock_proc

            with pytest.raises(NativeExecutorError, match="Script exited with code 1"):
                executor.run_script("test_env", script, [])


@pytest.mark.smoke_minimal
def test_native_executor_real_conda_detection():
    """Verify we can find a real conda/mamba/micromamba on this system."""
    try:
        executor = NativeExecutor()
        assert executor.conda_path is not None
        assert Path(executor.conda_path).exists()
    except NativeExecutorError:
        pytest.skip("No conda/mamba/micromamba found on system")


@pytest.mark.smoke_minimal
def test_native_executor_env_missing_skip_logic():
    """Demonstrate how tests can skip if an environment is missing."""
    executor = NativeExecutor(conda_path="conda")
    with patch.object(NativeExecutor, "env_exists", return_value=False):
        if not executor.env_exists("missing_env"):
            pytest.skip("Skipping because environment is missing")
