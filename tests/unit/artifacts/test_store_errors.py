from __future__ import annotations

import errno
from pathlib import Path

import pytest

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.errors import ArtifactStoreError


def test_import_file_disk_full_persists_log_ref(tmp_path: Path, monkeypatch) -> None:
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    read_root = tmp_path / "data"
    read_root.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[read_root],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    src = read_root / "in.txt"
    src.write_text("hello")

    store = ArtifactStore(config)

    def _copy2(_src: Path, _dest: Path) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("bioimage_mcp.artifacts.store.shutil.copy2", _copy2)

    with pytest.raises(ArtifactStoreError) as excinfo:
        store.import_file(src, artifact_type="BioImageRef", format="text")

    details = excinfo.value.details
    assert isinstance(details, dict)
    assert details.get("cause") == "ENOSPC"
    assert details.get("log_ref_id")

    log_ref = store.get(str(details["log_ref_id"]))
    assert log_ref.type == "LogRef"
