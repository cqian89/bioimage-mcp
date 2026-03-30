from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dev_and_test_extras_include_numpydoc() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extras = pyproject["project"]["optional-dependencies"]

    assert "numpydoc" in extras["dev"]
    assert "numpydoc" in extras["test"]
