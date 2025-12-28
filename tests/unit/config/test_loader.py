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


def test_default_config_allows_artifact_store_reads(tmp_path: Path) -> None:
    """Verify default config includes artifact_store_root in fs_allowlist_read."""
    config = load_config(
        global_path=tmp_path / "nope" / "config.yaml",
        local_path=tmp_path / "also_nope" / "config.yaml",
    )

    assert config.fs_allowlist_read
    assert config.artifact_store_root in config.fs_allowlist_read


def test_load_config_rejects_non_absolute_roots(tmp_path: Path) -> None:
    global_cfg = tmp_path / "home" / ".bioimage-mcp" / "config.yaml"
    global_cfg.parent.mkdir(parents=True)
    global_cfg.write_text("artifact_store_root: relative/path\n")

    with pytest.raises(ValueError, match="absolute"):
        load_config(global_path=global_cfg, local_path=tmp_path / "missing.yaml")


def test_load_config_session_ttl_hours_defaults_to_24(tmp_path: Path) -> None:
    """session_ttl_hours should default to 24 when not configured."""
    config = load_config(
        global_path=tmp_path / "nope" / "config.yaml",
        local_path=tmp_path / "also_nope" / "config.yaml",
    )

    assert config.session_ttl_hours == 24


def test_load_config_session_ttl_hours_from_config(tmp_path: Path) -> None:
    """session_ttl_hours should be configurable via YAML."""
    global_cfg = tmp_path / "home" / ".bioimage-mcp" / "config.yaml"
    global_cfg.parent.mkdir(parents=True)
    global_cfg.write_text(
        """\
artifact_store_root: /abs/artifacts
session_ttl_hours: 48
"""
    )

    config = load_config(global_path=global_cfg, local_path=tmp_path / "missing.yaml")

    assert config.session_ttl_hours == 48


def test_load_config_session_ttl_hours_rejects_zero(tmp_path: Path) -> None:
    """session_ttl_hours must be >= 1."""
    global_cfg = tmp_path / "home" / ".bioimage-mcp" / "config.yaml"
    global_cfg.parent.mkdir(parents=True)
    global_cfg.write_text(
        """\
artifact_store_root: /abs/artifacts
session_ttl_hours: 0
"""
    )

    with pytest.raises(ValueError, match="session_ttl_hours must be >= 1"):
        load_config(global_path=global_cfg, local_path=tmp_path / "missing.yaml")


def test_load_config_session_ttl_hours_rejects_negative(tmp_path: Path) -> None:
    """session_ttl_hours must be >= 1."""
    global_cfg = tmp_path / "home" / ".bioimage-mcp" / "config.yaml"
    global_cfg.parent.mkdir(parents=True)
    global_cfg.write_text(
        """\
artifact_store_root: /abs/artifacts
session_ttl_hours: -5
"""
    )

    with pytest.raises(ValueError, match="session_ttl_hours must be >= 1"):
        load_config(global_path=global_cfg, local_path=tmp_path / "missing.yaml")
