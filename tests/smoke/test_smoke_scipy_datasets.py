from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_dataset_presence():
    """Assert that required datasets for reproducible smoke tests exist."""
    required_files = [
        "datasets/synthetic/test.tif",
    ]

    # Assume running from repo root
    for rel_path in required_files:
        path = Path(rel_path)
        assert path.exists(), f"Missing required dataset: {rel_path}"
        assert path.is_file(), f"Path exists but is not a file: {rel_path}"
