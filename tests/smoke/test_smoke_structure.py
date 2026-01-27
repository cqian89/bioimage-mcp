from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.smoke_minimal
def test_smoke_directories_exist() -> None:
    """Assert required smoke test directories exist."""
    smoke_dir = Path(__file__).parent

    reference_scripts_dir = smoke_dir / "reference_scripts"
    utils_dir = smoke_dir / "utils"

    assert reference_scripts_dir.is_dir(), f"Missing directory: {reference_scripts_dir}"
    assert utils_dir.is_dir(), f"Missing directory: {utils_dir}"


@pytest.mark.smoke_minimal
def test_smoke_init_files_exist() -> None:
    """Assert __init__.py files exist in smoke test directories."""
    smoke_dir = Path(__file__).parent

    reference_scripts_init = smoke_dir / "reference_scripts" / "__init__.py"
    utils_init = smoke_dir / "utils" / "__init__.py"

    assert reference_scripts_init.exists(), f"Missing file: {reference_scripts_init}"
    assert utils_init.exists(), f"Missing file: {utils_init}"
