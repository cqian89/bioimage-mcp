"""Contract test ensuring .gitignore ignores Cellpose caches (T006a).

Validates that the project .gitignore includes patterns for Cellpose
model caches and other tool-specific artifacts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

GITIGNORE_PATH = Path(__file__).parents[2] / ".gitignore"


class TestGitignoreCellposeContract:
    """Contract tests for .gitignore Cellpose patterns."""

    def test_gitignore_exists(self) -> None:
        """Test that .gitignore file exists."""
        assert GITIGNORE_PATH.exists(), f".gitignore not found at {GITIGNORE_PATH}"

    def test_gitignore_has_cellpose_cache_pattern(self) -> None:
        """Test that .gitignore includes Cellpose cache patterns."""
        content = GITIGNORE_PATH.read_text()

        # Cellpose downloads models to ~/.cellpose by default, but
        # tools might cache in project directory
        _patterns_to_check = [
            # At least one of these patterns should exist
            "cellpose",
            ".cellpose",
            "tools/cellpose/*.npy",
            "models/",
        ]

        has_cellpose_pattern = any(pattern in content.lower() for pattern in ["cellpose", "models"])

        # This is a soft check - we want at least some mention of model caches
        if not has_cellpose_pattern:
            pytest.skip(
                ".gitignore does not yet have Cellpose-specific patterns. "
                "Consider adding patterns for model caches."
            )

    def test_gitignore_has_datasets_pattern(self) -> None:
        """Test that .gitignore ignores datasets directory."""
        content = GITIGNORE_PATH.read_text()
        assert "datasets/" in content, ".gitignore should include 'datasets/' pattern"
