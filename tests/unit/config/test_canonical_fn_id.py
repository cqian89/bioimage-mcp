from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.config.loader import is_canonical_fn_id, validate_manifest_fn_ids
from bioimage_mcp.registry.manifest_schema import Function, ToolManifest


def _manifest_with_fn(fn_id: str) -> ToolManifest:
    return ToolManifest(
        manifest_version="0.0",
        tool_id="tools.base",
        tool_version="0.1.0",
        env_id="bioimage-mcp-base",
        entrypoint="bioimage_mcp_base/entrypoint.py",
        manifest_path=Path("/tmp/manifest.yaml"),
        manifest_checksum="test",
        functions=[
            Function(
                fn_id=fn_id,
                tool_id="tools.base",
                name="Test Function",
                description="Test",
            )
        ],
    )


def test_is_canonical_fn_id_accepts_full_name() -> None:
    assert is_canonical_fn_id("base.bioimage_mcp_base.preprocess.gaussian")


def test_is_canonical_fn_id_rejects_short_name() -> None:
    assert not is_canonical_fn_id("base.gaussian")


def test_is_canonical_fn_id_allows_meta_describe_by_default() -> None:
    assert is_canonical_fn_id("meta.describe")
    assert not is_canonical_fn_id("meta.describe", allow_meta=False)


def test_validate_manifest_fn_ids_rejects_noncanonical() -> None:
    manifest = _manifest_with_fn("base.gaussian")

    with pytest.raises(ValueError, match="Non-canonical fn_id"):
        validate_manifest_fn_ids([manifest], allow_meta=False)


def test_validate_manifest_fn_ids_accepts_canonical() -> None:
    manifest = _manifest_with_fn("base.bioimage_mcp_base.preprocess.gaussian")

    validate_manifest_fn_ids([manifest])
