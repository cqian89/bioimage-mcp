from __future__ import annotations

from pathlib import Path
import pytest
from tests.fixtures.lfs_helpers import is_lfs_pointer


def test_is_lfs_pointer_real_file(tmp_path: Path):
    # Create a real file that is small but not an LFS pointer
    f = tmp_path / "real.txt"
    f.write_text("This is a real file content.")
    assert is_lfs_pointer(f) is False


def test_is_lfs_pointer_lfs_mock(tmp_path: Path):
    # Create a file that looks like an LFS pointer
    f = tmp_path / "pointer.lfs"
    f.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:1234567890\nsize 100\n")
    assert is_lfs_pointer(f) is True


def test_is_lfs_pointer_large_file(tmp_path: Path):
    # Create a large file
    f = tmp_path / "large.bin"
    f.write_bytes(b"\0" * 2048)
    assert is_lfs_pointer(f) is False


def test_is_lfs_pointer_directory(tmp_path: Path):
    assert is_lfs_pointer(tmp_path) is False
