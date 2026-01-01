from __future__ import annotations

from bioimage_mcp.config.loader import find_repo_root
from bioimage_mcp.registry.loader import load_manifests


def _load_repo_manifests() -> list:
    repo_root = find_repo_root()
    assert repo_root is not None, "Repository root not found for manifest loading"

    manifests, diagnostics = load_manifests([repo_root / "tools"])
    assert not diagnostics, f"Manifest diagnostics encountered: {diagnostics}"
    return manifests


def test_base_manifest_present_and_builtin_absent() -> None:
    manifests = _load_repo_manifests()
    tool_ids = {manifest.tool_id for manifest in manifests}

    assert "tools.base" in tool_ids
    assert "tools.builtin" not in tool_ids


def test_base_manifest_includes_gaussian_and_convert() -> None:
    manifests = _load_repo_manifests()
    base_manifest = next(manifest for manifest in manifests if manifest.tool_id == "tools.base")
    fn_ids = {fn.fn_id for fn in base_manifest.functions}

    assert "base.skimage.filters.gaussian" in fn_ids
    assert "base.bioio.export" in fn_ids
    # Verify legacy wrapper is gone
    assert "base.wrapper.io.convert_to_ome_zarr" not in fn_ids
