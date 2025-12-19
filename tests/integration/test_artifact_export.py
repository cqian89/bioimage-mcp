from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_export_enforces_write_allowlist(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    allowed_write_root = tmp_path / "allowed_write"
    denied_write_root = tmp_path / "denied_write"
    allowed_write_root.mkdir()
    denied_write_root.mkdir()

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[allowed_write_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    src = tmp_path / "in.txt"
    src.write_text("hello")
    ref = store.import_file(src, artifact_type="LogRef", format="text")

    with pytest.raises(PermissionError):
        store.export(ref.ref_id, denied_write_root / "out.txt")

    exported = store.export(ref.ref_id, allowed_write_root / "out.txt")
    assert exported.exists()
    assert exported.read_text() == "hello"
