from pathlib import Path

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import connect


@pytest.mark.integration
def test_hierarchical_listing_skimage(tmp_path):
    """Verify that list_tools(path='base.skimage') returns sub-modules/functions."""
    # Setup
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    tools_root = Path(__file__).parent.parent.parent / "tools"

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tools_root],
        fs_allowlist_write=[artifacts_root],
    )

    conn = connect(config)
    discovery = DiscoveryService(conn)

    # Load and index manifests to ensure DB is populated
    manifests, diagnostics = load_manifests([tools_root])
    assert not diagnostics, f"Manifest diagnostics: {diagnostics}"
    for manifest in manifests:
        discovery.upsert_tool(
            tool_id=manifest.tool_id,
            name=manifest.name,
            description=manifest.description,
            tool_version=manifest.tool_version,
            env_id=manifest.env_id,
            manifest_path=str(manifest.manifest_path),
            installed=True,
            available=True,
        )
        for fn in manifest.functions:
            discovery.upsert_function(
                fn_id=fn.fn_id,
                tool_id=manifest.tool_id,
                name=fn.name,
                description=fn.description,
                tags=fn.tags,
                inputs=[port.model_dump() for port in fn.inputs],
                outputs=[port.model_dump() for port in fn.outputs],
                params_schema=fn.params_schema,
                introspection_source=fn.introspection_source,
            )

    # Now list base.skimage
    # This should include the dynamically discovered sub-modules.
    result_skimage = discovery.list_tools(path="base.skimage")
    paths_skimage = [t["full_path"] for t in result_skimage["tools"]]
    print(f"\nPATHS SKIMAGE: {paths_skimage}")

    assert "base.skimage.filters" in paths_skimage
    assert "base.skimage.transform" in paths_skimage
    assert "base.skimage.morphology" in paths_skimage
