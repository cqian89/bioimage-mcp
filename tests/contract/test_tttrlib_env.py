"""Contract test for tttrlib environment configuration (Phase 1)."""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

TTTRLIB_ENV_PATH = Path(__file__).parents[2] / "envs" / "bioimage-mcp-tttrlib.yaml"
TTTRLIB_API_SCHEMA_PATH = (
    Path(__file__).parents[2] / "tools" / "tttrlib" / "schema" / "tttrlib_api.json"
)


class TestTTTRLibEnvContract:
    """Contract tests for tttrlib environment and schema definition."""

    def test_env_file_exists(self) -> None:
        """Test that the tttrlib env file exists."""
        assert TTTRLIB_ENV_PATH.exists(), f"tttrlib env definition not found at {TTTRLIB_ENV_PATH}"

    def test_env_python_version(self) -> None:
        """Test that tttrlib environment uses Python 3.12."""
        if not TTTRLIB_ENV_PATH.exists():
            pytest.fail("tttrlib env file does not exist")

        with open(TTTRLIB_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        dependencies = env_def.get("dependencies", [])
        python_dep = next(
            (dep for dep in dependencies if isinstance(dep, str) and dep.startswith("python")), None
        )

        assert python_dep is not None, "Python version must be specified"
        assert "3.12" in python_dep, (
            f"tttrlib requires Python 3.12 for C++ bindings stability, got {python_dep}"
        )

    def test_env_includes_tttrlib(self) -> None:
        """Test that tttrlib is included in dependencies from the correct channel."""
        if not TTTRLIB_ENV_PATH.exists():
            pytest.skip("tttrlib env file not yet created")

        with open(TTTRLIB_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        channels = env_def.get("channels", [])
        assert "tpeulen" in channels or any(
            "tpeulen" in str(dep) for dep in env_def.get("dependencies", [])
        ), "Environment should use tpeulen channel or specify the channel for tttrlib"

        dependencies = env_def.get("dependencies", [])
        tttrlib_found = False
        for dep in dependencies:
            if isinstance(dep, str) and "tttrlib" in dep:
                tttrlib_found = True
                break

        assert tttrlib_found, "tttrlib not found in environment dependencies"

    def test_api_schema_file_exists(self) -> None:
        """Test that the tttrlib API schema version file exists."""
        assert TTTRLIB_API_SCHEMA_PATH.exists(), (
            f"tttrlib API schema file not found at {TTTRLIB_API_SCHEMA_PATH}"
        )

    def test_env_name(self) -> None:
        """Test that the environment name is correct."""
        if not TTTRLIB_ENV_PATH.exists():
            pytest.skip("tttrlib env file not yet created")

        with open(TTTRLIB_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        assert env_def.get("name") == "bioimage-mcp-tttrlib"
