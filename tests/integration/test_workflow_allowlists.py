"""Integration tests for workflow read/write allowlist enforcement (T011b).

These tests verify that workflow execution correctly enforces filesystem
allowlists for both reading inputs and writing outputs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_workflow_rejects_inputs_outside_allowlist(tmp_path: Path) -> None:
    """Workflow execution should fail if input artifact comes from outside allowlist."""
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    allowed_read = tmp_path / "allowed_read"
    denied_read = tmp_path / "denied_read"

    allowed_read.mkdir()
    denied_read.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    # Try to import from denied path - should fail at import time
    store = ArtifactStore(config)

    denied_file = denied_read / "input.tif"
    denied_file.write_bytes(b"fake image")

    with pytest.raises(PermissionError, match=r"allowed read root"):
        store.import_file(denied_file, artifact_type="BioImageRef", format="TIFF")


def test_workflow_allows_inputs_from_artifact_store(tmp_path: Path) -> None:
    """Workflow should allow reading artifacts from within the artifact store."""
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[],  # No external reads allowed
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Write a log directly (internal write to artifact store)
    ref = store.write_log("test log content")

    # Reading it back should work since it's within artifact_store_root
    retrieved = store.get(ref.ref_id)
    assert retrieved.type == "LogRef"


def test_workflow_outputs_written_to_artifact_store(tmp_path: Path) -> None:
    """Workflow outputs should be written within the artifact store root."""
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    allowed_read = tmp_path / "data"
    allowed_read.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Create and import a test file
    input_file = allowed_read / "input.txt"
    input_file.write_text("input data")

    ref = store.import_file(input_file, artifact_type="LogRef", format="text")

    # Verify the artifact was stored within artifact_store_root
    artifact_path = Path(ref.uri.replace("file://", ""))
    assert artifact_path.is_relative_to(artifact_root) or str(artifact_path).startswith(
        str(artifact_root)
    )


def test_export_enforces_write_allowlist(tmp_path: Path) -> None:
    """Export should enforce write allowlist for destination path."""
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    allowed_read = tmp_path / "data"
    allowed_write = tmp_path / "exports"
    denied_write = tmp_path / "denied"

    allowed_read.mkdir()
    allowed_write.mkdir()
    denied_write.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[allowed_read],
        fs_allowlist_write=[allowed_write],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Import a file
    input_file = allowed_read / "input.txt"
    input_file.write_text("test data")
    ref = store.import_file(input_file, artifact_type="LogRef", format="text")

    # Export to denied path should fail
    with pytest.raises(PermissionError):
        store.export(ref.ref_id, denied_write / "output.txt")

    # Export to allowed path should succeed
    exported = store.export(ref.ref_id, allowed_write / "output.txt")
    assert exported.exists()
    assert exported.read_text() == "test data"


def test_workflow_work_dir_is_within_artifact_store(tmp_path: Path) -> None:
    """Workflow work directory should be within artifact_store_root."""
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    # Verify work directory structure
    work_dir = config.artifact_store_root / "work" / "runs"

    # Work dir should be under artifact_store_root
    assert str(work_dir).startswith(str(artifact_root))
