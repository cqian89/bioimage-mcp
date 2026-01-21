from __future__ import annotations

from pathlib import Path

import pytest


def is_lfs_pointer(path: Path) -> bool:
    """Check if a file is a Git LFS pointer."""
    if not path.is_file() or path.stat().st_size > 1024:
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(100).decode("utf-8", errors="ignore")
            return "version https://git-lfs.github.com/spec/v1" in head
    except Exception:
        return False


def skip_if_lfs_pointer(path: Path) -> None:
    """Pytest helper to skip a test if a dataset file is an LFS pointer."""
    if is_lfs_pointer(path):
        pytest.skip(f"Dataset '{path}' is a Git LFS pointer (content not fetched)")
