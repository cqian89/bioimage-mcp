from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_fs_policy_denies_reads_and_writes_outside_allowlists(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    allowed_read_root = tmp_path / "data"
    denied_root = tmp_path / "denied"

    allowed_read_root.mkdir()
    denied_root.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[allowed_read_root],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    denied_src = denied_root / "input.txt"
    denied_src.write_text("nope")

    with pytest.raises(PermissionError, match=r"allowed read root"):
        store.import_file(denied_src, artifact_type="LogRef", format="text")

    allowed_src = allowed_read_root / "input.txt"
    allowed_src.write_text("ok")
    ref = store.import_file(allowed_src, artifact_type="LogRef", format="text")

    denied_dest = denied_root / "export.txt"
    with pytest.raises(PermissionError, match=r"allowed write root"):
        store.export(ref.ref_id, denied_dest)
