from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.config.fs_policy import assert_path_allowed
from bioimage_mcp.config.schema import Config


def test_fs_policy_allows_path_under_read_root(tmp_path: Path) -> None:
    read_root = tmp_path / "data"
    read_root.mkdir()
    target = read_root / "image.ome.tif"
    target.write_text("x")

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[read_root],
        fs_allowlist_write=[tmp_path / "artifacts"],
        fs_denylist=[],
    )

    assert_path_allowed("read", target, config)


def test_fs_policy_denies_path_under_denylist(tmp_path: Path) -> None:
    read_root = tmp_path / "data"
    deny_root = read_root / "private"
    deny_root.mkdir(parents=True)
    target = deny_root / "secret.txt"
    target.write_text("x")

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[read_root],
        fs_allowlist_write=[tmp_path / "artifacts"],
        fs_denylist=[deny_root],
    )

    with pytest.raises(PermissionError):
        assert_path_allowed("read", target, config)


def test_fs_policy_denies_path_outside_allowlist(tmp_path: Path) -> None:
    read_root = tmp_path / "data"
    read_root.mkdir()

    outside = tmp_path / "other" / "file.txt"
    outside.parent.mkdir(parents=True)
    outside.write_text("x")

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[read_root],
        fs_allowlist_write=[tmp_path / "artifacts"],
        fs_denylist=[],
    )

    with pytest.raises(PermissionError):
        assert_path_allowed("read", outside, config)
