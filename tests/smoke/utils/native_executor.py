from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class NativeExecutorError(Exception):
    """Base exception for execution failures."""

    pass


class EnvironmentNotFoundError(NativeExecutorError):
    """Raised when env doesn't exist."""

    pass


class NativeExecutor:
    def __init__(self, conda_path: str | None = None):
        """Initialize with conda executable. Auto-detected if not provided."""
        if conda_path:
            self.conda_path = conda_path
        else:
            self.conda_path = self._detect_conda()

    def _detect_conda(self) -> str:
        for cmd in ["micromamba", "mamba", "conda"]:
            path = shutil.which(cmd)
            if path:
                return path
        raise NativeExecutorError("Could not find conda, mamba, or micromamba executable.")

    def env_exists(self, env_name: str) -> bool:
        """Check if conda environment exists."""
        try:
            output = subprocess.check_output(
                [self.conda_path, "env", "list"], stderr=subprocess.STDOUT
            ).decode()
            for line in output.splitlines():
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if parts and parts[0] == env_name:
                    return True
            return False
        except subprocess.CalledProcessError as e:
            raise NativeExecutorError(f"Failed to list conda environments: {e.output.decode()}")

    def run_script(
        self,
        env_name: str,
        script_path: Path,
        args: list[str],
        timeout: int = 300,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """Execute script and parse JSON output."""
        if not self.env_exists(env_name):
            raise EnvironmentNotFoundError(f"Conda environment '{env_name}' not found.")

        cmd = [self.conda_path, "run", "-n", env_name, "python", str(script_path)] + args

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)

            if result.returncode != 0:
                raise NativeExecutorError(
                    f"Script exited with code {result.returncode}.\n"
                    f"STDOUT: {result.stdout}\n"
                    f"STDERR: {result.stderr}"
                )

            try:
                # Find the first line that looks like JSON or just use the last line?
                # Usually we expect the script to only print JSON to stdout.
                # However, some things might print noise.
                # For now, let's assume it's just JSON.
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise NativeExecutorError(
                    f"Failed to parse JSON output: {e}\nOutput: {result.stdout}"
                )

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Script execution timed out after {timeout} seconds.")
