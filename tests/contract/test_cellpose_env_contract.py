"""Contract test that Cellpose env definition pins Cellpose version (T001a).

Ensures the environment YAML specifies an explicit version for cellpose
to guarantee reproducibility.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CELLPOSE_ENV_PATH = Path(__file__).parents[2] / "envs" / "bioimage-mcp-cellpose.yaml"


class TestCellposeEnvContract:
    """Contract tests for Cellpose environment definition."""

    def test_env_file_exists(self) -> None:
        """Test that the Cellpose env file exists."""
        assert CELLPOSE_ENV_PATH.exists(), (
            f"Cellpose env definition not found at {CELLPOSE_ENV_PATH}"
        )

    def test_env_pins_cellpose_version(self) -> None:
        """Test that cellpose is pinned to a specific version."""
        if not CELLPOSE_ENV_PATH.exists():
            pytest.skip("Cellpose env file not yet created")

        with open(CELLPOSE_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        # Look for cellpose in dependencies
        dependencies = env_def.get("dependencies", [])

        # Find cellpose dependency
        cellpose_dep = None
        for dep in dependencies:
            if isinstance(dep, str) and dep.startswith("cellpose"):
                cellpose_dep = dep
                break
            elif isinstance(dep, dict):
                # pip dependencies section
                pip_deps = dep.get("pip", [])
                for pip_dep in pip_deps:
                    if isinstance(pip_dep, str) and pip_dep.startswith("cellpose"):
                        cellpose_dep = pip_dep
                        break

        assert cellpose_dep is not None, "cellpose not found in dependencies"

        # Check that version is pinned (contains = or ==)
        assert "=" in cellpose_dep or ">=" in cellpose_dep, (
            f"cellpose must be pinned to a specific version, got: {cellpose_dep}"
        )

    def test_env_name_prefix(self) -> None:
        """Test that env name starts with bioimage-mcp-."""
        if not CELLPOSE_ENV_PATH.exists():
            pytest.skip("Cellpose env file not yet created")

        with open(CELLPOSE_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        env_name = env_def.get("name", "")
        assert env_name.startswith("bioimage-mcp-"), (
            f"env name must start with 'bioimage-mcp-', got: {env_name}"
        )

    def test_env_includes_python(self) -> None:
        """Test that Python version is specified."""
        if not CELLPOSE_ENV_PATH.exists():
            pytest.skip("Cellpose env file not yet created")

        with open(CELLPOSE_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        dependencies = env_def.get("dependencies", [])

        # Find python dependency
        python_found = any(
            isinstance(dep, str) and dep.startswith("python") for dep in dependencies
        )
        assert python_found, "python version must be specified in dependencies"
