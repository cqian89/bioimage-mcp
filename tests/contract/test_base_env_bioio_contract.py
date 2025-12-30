"""Contract test for bioio dependencies in base environment (T001).

Ensures bioimage-mcp-base includes core bioio and essential plugins
for standardized image I/O.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

BASE_ENV_PATH = Path(__file__).parents[2] / "envs" / "bioimage-mcp-base.yaml"


class TestBaseEnvBioioContract:
    """Contract tests for bioio in base environment."""

    def test_env_file_exists(self) -> None:
        """Test that the base env file exists."""
        assert BASE_ENV_PATH.exists(), f"Base env definition not found at {BASE_ENV_PATH}"

    def test_includes_required_bioio_deps(self) -> None:
        """Test that base env includes core bioio and interchange plugins."""
        if not BASE_ENV_PATH.exists():
            pytest.skip("Base env file not found")

        with open(BASE_ENV_PATH) as f:
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
        assert any(d.split("=")[0].strip() == "bioio" for d in all_deps if isinstance(d, str)), (
            "bioio core must be in base environment"
        )

        # Check for interchange formats
        assert any("bioio-ome-tiff" in d for d in all_deps if isinstance(d, str)), (
            "bioio-ome-tiff plugin must be in base environment"
        )
        assert any("bioio-ome-zarr" in d for d in all_deps if isinstance(d, str)), (
            "bioio-ome-zarr plugin must be in base environment"
        )

    def test_proprietary_reader_policy(self) -> None:
        """Test that base env includes at least one CZI-capable reader.

        The policy (T001) requires CZI ingest support, either via bioio-czi
        or bioio-bioformats.
        """
        if not BASE_ENV_PATH.exists():
            pytest.skip("Base env file not found")

        with open(BASE_ENV_PATH) as f:
            env_def = yaml.safe_load(f)

        dependencies = env_def.get("dependencies", [])
        all_deps = []
        for dep in dependencies:
            if isinstance(dep, str):
                all_deps.append(dep)
            elif isinstance(dep, dict) and "pip" in dep:
                all_deps.extend(dep["pip"])

        czi_support = any(
            "bioio-czi" in d or "bioio-bioformats" in d for d in all_deps if isinstance(d, str)
        )
        assert czi_support, (
            "Base environment must support CZI ingest (bioio-czi or bioio-bioformats)"
        )
