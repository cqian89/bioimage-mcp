from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dev_and_test_extras_include_numpydoc() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extras = pyproject["project"]["optional-dependencies"]

    assert "numpydoc" in extras["dev"]
    assert "numpydoc" in extras["test"]


def test_dev_and_test_extras_cover_core_ci_runtime_needs() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extras = pyproject["project"]["optional-dependencies"]
    required = {
        "matplotlib",
        "bioio-czi==2.4.2",
        "aicspylibczi==3.3.1",
        "pylibczirw==5.1.1",
        "bioio-imageio==1.3.0",
        "bioio-tifffile==1.3.0",
    }

    assert required.issubset(set(extras["dev"]))
    assert required.issubset(set(extras["test"]))
