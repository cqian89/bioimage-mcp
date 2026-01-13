"""Contract test for matplotlib dependency in base environment."""

from __future__ import annotations

from pathlib import Path

import yaml

BASE_ENV_PATH = Path(__file__).parents[2] / "envs" / "bioimage-mcp-base.yaml"


class TestMatplotlibEnvContract:
    """Contract tests for matplotlib in base environment."""

    def test_matplotlib_dependency_declared(self) -> None:
        """Test that envs/bioimage-mcp-base.yaml declares matplotlib>=3.8."""
        assert BASE_ENV_PATH.exists(), f"Base env definition not found at {BASE_ENV_PATH}"

        with open(BASE_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        dependencies = env_def.get("dependencies", [])

        # Check if matplotlib>=3.8 is in the conda dependencies
        conda_deps = [d for d in dependencies if isinstance(d, str)]

        assert "matplotlib>=3.8" in conda_deps, "matplotlib>=3.8 not found in conda dependencies"
