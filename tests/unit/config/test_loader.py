from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.config.loader import load_config


def test_load_config_prefers_local_over_global(tmp_path: Path) -> None:
    global_cfg = tmp_path / "home" / ".bioimage-mcp" / "config.yaml"
    local_cfg = tmp_path / "project" / ".bioimage-mcp" / "config.yaml"
    global_cfg.parent.mkdir(parents=True)
    local_cfg.parent.mkdir(parents=True)

    global_cfg.write_text(
        """
artifact_store_root: /abs/global/artifacts
fs_allowlist_read: [/abs/data]
default_pagination_limit: 10
""".lstrip()
    )
    local_cfg.write_text(
        """
artifact_store_root: /abs/local/artifacts
max_pagination_limit: 123
""".lstrip()
    )

    config = load_config(global_path=global_cfg, local_path=local_cfg)

    assert config.artifact_store_root == Path("/abs/local/artifacts")
    assert config.fs_allowlist_read == [Path("/abs/data")]
    assert config.default_pagination_limit == 10
    assert config.max_pagination_limit == 123


def test_load_config_missing_files_uses_defaults(tmp_path: Path) -> None:
    config = load_config(
        global_path=tmp_path / "nope" / "config.yaml",
        local_path=tmp_path / "also_nope" / "config.yaml",
    )

    assert config.default_pagination_limit > 0
    assert config.max_pagination_limit >= config.default_pagination_limit


def test_load_config_rejects_non_absolute_roots(tmp_path: Path) -> None:
    global_cfg = tmp_path / "home" / ".bioimage-mcp" / "config.yaml"
    global_cfg.parent.mkdir(parents=True)
    global_cfg.write_text("artifact_store_root: relative/path\n")

    with pytest.raises(ValueError, match="absolute"):
        load_config(global_path=global_cfg, local_path=tmp_path / "missing.yaml")
