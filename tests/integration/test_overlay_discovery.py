from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.loader import find_repo_root
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def discovery_service(tmp_path: Path):
    repo_root = find_repo_root()
    assert repo_root is not None
    tools_root = repo_root / "tools"
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tools_root],
        fs_allowlist_write=[artifacts_root],
    )

    conn = connect(config)
    service = DiscoveryService(conn)

    # Load manifests into index
    manifests, diagnostics = load_manifests([tools_root])
    # Note: load_manifests already applies overlays if they exist in manifest.yaml
    for manifest in manifests:
        service.upsert_tool(
            tool_id=manifest.tool_id,
            tool_version=manifest.tool_version,
            name=manifest.name,
            description=manifest.description,
            env_id=manifest.env_id,
            manifest_path=str(manifest.manifest_path),
            installed=True,
            available=True,
        )
        for fn in manifest.functions:
            service.upsert_function(
                fn_id=fn.fn_id,
                tool_id=manifest.tool_id,
                name=fn.name,
                description=fn.description,
                tags=fn.tags,
                inputs=[p.model_dump() for p in fn.inputs],
                outputs=[p.model_dump() for p in fn.outputs],
                params_schema=fn.params_schema,
            )

    return service


@pytest.mark.integration
def test_overlay_applied_to_gaussian(discovery_service: DiscoveryService):
    """
    T026: Assert that overlays defined in tools/base/manifest.yaml
    are merged into dynamically discovered functions.
    """
    # 1) Overlay-applied hints.success_hints shows up in describe_function response.
    resp = discovery_service.describe_function(id="base.skimage.filters.gaussian")

    assert "hints" in resp, "Hints should be present in describe_function response"
    assert "success_hints" in resp["hints"]
    assert "next_steps" in resp["hints"]["success_hints"]
    assert (
        resp["hints"]["success_hints"]["next_steps"][0]["id"]
        == "base.skimage.morphology.remove_small_objects"
    )

    # 2) Overlay-applied tags show up in search_functions response.
    search_resp = discovery_service.search_functions(keywords="gaussian", limit=None, cursor=None)
    gaussian_fn = next(
        (f for f in search_resp["results"] if f["id"] == "base.skimage.filters.gaussian"), None
    )
    assert gaussian_fn is not None
    assert "denoise" in gaussian_fn["tags"]
    assert "smooth" in gaussian_fn["tags"]
    assert "Apply a Gaussian filter" in gaussian_fn["summary"]


@pytest.mark.integration
def test_overlay_applied_to_remove_small_objects(discovery_service: DiscoveryService):
    """
    T026: Assert that io_pattern affects ports for a label op.
    """
    # 3) Overlay-applied io_pattern affects described ports for a label op.
    resp = discovery_service.describe_function(id="base.skimage.morphology.remove_small_objects")

    # We want labels_to_labels which should be LabelImageRef -> LabelImageRef
    assert resp["inputs"]["image"]["type"] == "LabelImageRef"
    assert resp["outputs"]["labels"]["type"] == "LabelImageRef"
