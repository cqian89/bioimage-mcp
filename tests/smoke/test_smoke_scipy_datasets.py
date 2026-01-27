import os
import pytest
from pathlib import Path


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_dataset_presence():
    """Assert that required datasets for reproducible smoke tests exist."""
    required_files = [
        "datasets/synthetic/test.tif",
        "datasets/sample_data/measurements.csv",
    ]

    root_dir = Path(__file__).parent.parent.parent

    for rel_path in required_files:
        full_path = root_dir / rel_path
        assert full_path.exists(), f"Missing required dataset: {rel_path}"
        assert full_path.is_file(), f"Path exists but is not a file: {rel_path}"
