"""Integration tests for artifact import allowlist enforcement (T011a).

These tests verify that the artifact store correctly enforces filesystem
allowlists when importing files and directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_import_file_enforces_read_allowlist(tmp_path: Path) -> None:
    """Import from non-allowed path should raise PermissionError."""
    artifact_root = tmp_path / "artifacts"
    allowed_read = tmp_path / "allowed"
    denied_read = tmp_path / "denied"

    allowed_read.mkdir()
    denied_read.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Create test file in denied path
    denied_file = denied_read / "image.tif"
    denied_file.write_bytes(b"fake tiff")

    with pytest.raises(PermissionError, match=r"allowed read root"):
        store.import_file(denied_file, artifact_type="BioImageRef", format="TIFF")


def test_import_file_allows_from_allowlisted_path(tmp_path: Path) -> None:
    """Import from allowed path should succeed."""
    artifact_root = tmp_path / "artifacts"
    allowed_read = tmp_path / "allowed"

    allowed_read.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Create test file in allowed path
    allowed_file = allowed_read / "image.tif"
    allowed_file.write_bytes(b"fake tiff")

    ref = store.import_file(allowed_file, artifact_type="BioImageRef", format="TIFF")
    assert ref.type == "BioImageRef"
    assert ref.format == "TIFF"
    assert ref.size_bytes > 0


def test_import_file_allows_from_artifact_store_root(tmp_path: Path) -> None:
    """Import from within artifact store root should succeed (implicit read access)."""
    artifact_root = tmp_path / "artifacts"
    work_dir = artifact_root / "work"
    work_dir.mkdir(parents=True)

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[],  # No external read allowed
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Create test file within artifact store root
    internal_file = work_dir / "output.txt"
    internal_file.write_text("internal")

    # Should succeed even without explicit read allowlist
    ref = store.import_file(internal_file, artifact_type="LogRef", format="text")
    assert ref.type == "LogRef"


def test_import_directory_enforces_read_allowlist(tmp_path: Path) -> None:
    """Import directory from non-allowed path should raise PermissionError."""
    artifact_root = tmp_path / "artifacts"
    allowed_read = tmp_path / "allowed"
    denied_read = tmp_path / "denied"

    allowed_read.mkdir()
    denied_dir = denied_read / "zarr_data"
    denied_dir.mkdir(parents=True)
    (denied_dir / "data.bin").write_bytes(b"data")

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    with pytest.raises(PermissionError, match=r"allowed read root"):
        store.import_directory(denied_dir, artifact_type="BioImageRef", format="OME-Zarr")


def test_import_respects_denylist(tmp_path: Path) -> None:
    """Denylist should override allowlist for import."""
    artifact_root = tmp_path / "artifacts"
    allowed_read = tmp_path / "allowed"
    denied_subdir = allowed_read / "denied"

    allowed_read.mkdir()
    denied_subdir.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[denied_subdir],
    )

    store = ArtifactStore(config)

    # Create file in denied subdir (within allowed parent)
    denied_file = denied_subdir / "secret.txt"
    denied_file.write_text("secret")

    with pytest.raises(PermissionError):
        store.import_file(denied_file, artifact_type="LogRef", format="text")
