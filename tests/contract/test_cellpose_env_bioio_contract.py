"""Contract test for bioio dependencies in Cellpose environment (T002).

Ensures bioimage-mcp-cellpose includes bioio and bioio-ome-tiff
for standardized image I/O.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CELLPOSE_ENV_PATH = Path(__file__).parents[2] / "envs" / "bioimage-mcp-cellpose.yaml"


class TestCellposeEnvBioioContract:
    """Contract tests for bioio in Cellpose environment."""

    def test_env_file_exists(self) -> None:
        """Test that the Cellpose env file exists."""
        assert CELLPOSE_ENV_PATH.exists(), (
            f"Cellpose env definition not found at {CELLPOSE_ENV_PATH}"
        )

    def test_includes_required_bioio_deps(self) -> None:
        """Test that Cellpose env includes bioio and OME-TIFF support."""
        if not CELLPOSE_ENV_PATH.exists():
            pytest.skip("Cellpose env file not found")

        with open(CELLPOSE_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        dependencies = env_def.get("dependencies", [])

        # Flatten all dependencies (including pip)
        all_deps = []
        for dep in dependencies:
            if isinstance(dep, str):
                all_deps.append(dep)
            elif isinstance(dep, dict) and "pip" in dep:
                all_deps.extend(dep["pip"])

        # Check for core bioio
        assert any(
            "bioio" == d.split("=")[0].split(">")[0].strip() for d in all_deps if isinstance(d, str)
        ), "bioio core must be in Cellpose environment"

        # Check for OME-TIFF support
        assert any("bioio-ome-tiff" in d for d in all_deps if isinstance(d, str)), (
            "bioio-ome-tiff plugin must be in Cellpose environment"
        )
