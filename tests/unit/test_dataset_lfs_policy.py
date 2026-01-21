from __future__ import annotations

from pathlib import Path

from tests.fixtures.lfs_helpers import is_lfs_pointer


def test_gitattributes_tracks_datasets():
    """Assert that .gitattributes tracks datasets/** with LFS."""
    gitattributes = Path(".gitattributes")
    assert gitattributes.exists(), ".gitattributes file not found"

    content = gitattributes.read_text()
    # Check for the specific rule: datasets/** filter=lfs
    assert "datasets/**" in content
    assert "filter=lfs" in content


def test_dataset_folders_have_readme():
    """Assert that each directory in datasets/ has a README.md."""
    datasets_dir = Path("datasets")
    assert datasets_dir.is_dir(), "datasets/ directory not found"

    # Get all subdirectories in datasets/
    # We exclude hidden directories like .git if they were to exist here
    dirs = [d for d in datasets_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    for d in dirs:
        readme = d / "README.md"
        assert readme.exists(), (
            f"Missing README.md in {d}. Every dataset folder must have a provenance README."
        )


def test_lfs_pointer_detection_logic(tmp_path: Path):
    """Verify that is_lfs_pointer correctly identifies LFS pointers."""
    # 1. Real file (not a pointer)
    real_file = tmp_path / "real.txt"
    real_file.write_text("This is a normal text file.")
    assert is_lfs_pointer(real_file) is False

    # 2. Valid LFS pointer
    pointer_content = (
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:4d6a1329c0f9157201c1f1f97486e96bb9e246990d98410260742a0468305f42\n"
        "size 12345\n"
    )
    pointer_file = tmp_path / "pointer.lfs"
    pointer_file.write_text(pointer_content)
    assert is_lfs_pointer(pointer_file) is True

    # 3. Large file (should not be treated as pointer even if it has the header)
    large_file = tmp_path / "large.bin"
    large_content = b"version https://git-lfs.github.com/spec/v1\n" + b"x" * 1100
    large_file.write_bytes(large_content)
    assert is_lfs_pointer(large_file) is False

    # 4. Directory should not be a pointer
    assert is_lfs_pointer(tmp_path) is False
