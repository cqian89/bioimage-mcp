from __future__ import annotations

from pathlib import Path

import pytest

from tests.smoke.utils.lfs_utils import is_lfs_pointer, skip_if_lfs_pointer


@pytest.mark.smoke_minimal
def test_is_lfs_pointer_detects_pointer(tmp_path: Path):
    """Test that is_lfs_pointer correctly identifies an LFS pointer file."""
    pointer_path = tmp_path / "pointer.txt"
    pointer_content = (
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:4d7a2dc572339a2731b295a2b697d4ac2e024500999603330c29782863ad24a1\n"
        "size 12345\n"
    )
    pointer_path.write_text(pointer_content)

    assert is_lfs_pointer(pointer_path) is True


@pytest.mark.smoke_minimal
def test_is_lfs_pointer_rejects_real_file(tmp_path: Path):
    """Test that is_lfs_pointer correctly identifies a real file (not a pointer)."""
    real_path = tmp_path / "real.txt"
    real_path.write_text("This is a real file with some content.")

    assert is_lfs_pointer(real_path) is False


@pytest.mark.smoke_minimal
def test_is_lfs_pointer_rejects_large_file(tmp_path: Path):
    """Test that is_lfs_pointer rejects files larger than 1024 bytes even if they look like pointers."""
    large_path = tmp_path / "large.txt"
    content = "version https://git-lfs.github.com/spec/v1\n" + ("x" * 2000)
    large_path.write_text(content)

    assert is_lfs_pointer(large_path) is False


@pytest.mark.smoke_minimal
def test_skip_if_lfs_pointer_skips(tmp_path: Path):
    """Test that skip_if_lfs_pointer raises pytest.skip for a pointer."""
    pointer_path = tmp_path / "pointer.txt"
    pointer_content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123"
    pointer_path.write_text(pointer_content)

    with pytest.raises(pytest.skip.Exception) as excinfo:
        skip_if_lfs_pointer(pointer_path)

    assert "is a Git LFS pointer" in str(excinfo.value)


@pytest.mark.smoke_minimal
def test_skip_if_lfs_pointer_does_not_skip_real_file(tmp_path: Path):
    """Test that skip_if_lfs_pointer does NOT skip for a real file."""
    real_path = tmp_path / "real.txt"
    real_path.write_text("Real content")

    # Should not raise any exception
    skip_if_lfs_pointer(real_path)
