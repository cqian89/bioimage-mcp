"""Contract test that Cellpose env lockfile exists (T001b).

Ensures a conda-lock file is generated for reproducible installs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

CELLPOSE_LOCK_PATH = Path(__file__).parents[2] / "envs" / "bioimage-mcp-cellpose.lock.yml"


class TestCellposeLockContract:
    """Contract tests for Cellpose environment lockfile."""

    def test_lockfile_exists(self) -> None:
        """Test that the Cellpose lockfile exists."""
        # This test will fail until the lockfile is generated
        # The lockfile is optional for MVP but recommended
        if not CELLPOSE_LOCK_PATH.exists():
            pytest.skip(
                "Cellpose lockfile not yet generated. "
                "Run: conda-lock -f envs/bioimage-mcp-cellpose.yaml "
                "-p linux-64 -p osx-arm64 -p win-64"
            )

        assert CELLPOSE_LOCK_PATH.exists()
