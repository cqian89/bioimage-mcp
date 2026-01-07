from bioimage_mcp.runtimes.persistent import PersistentWorkerManager


def test_resolve_entrypoint_fallback(tmp_path):
    """Test that it falls back to base entrypoint when no manifests match."""
    manager = PersistentWorkerManager(manifest_roots=[])

    # Should fall back to base entrypoint
    entrypoint = manager._resolve_entrypoint("non-existent-env")
    assert entrypoint.name == "entrypoint.py"
    assert "tools/base/bioimage_mcp_base" in str(entrypoint)


def test_resolve_entrypoint_from_manifest(tmp_path):
    """Test that it resolves entrypoint from a mock manifest."""
    tools_dir = tmp_path / "tools"
    mock_tool_dir = tools_dir / "mock_tool"
    mock_tool_dir.mkdir(parents=True)

    manifest_path = mock_tool_dir / "manifest.yaml"
    entrypoint_path = mock_tool_dir / "mock_entrypoint.py"
    entrypoint_path.write_text("print('hello')")

    manifest_content = """
manifest_version: "1.0"
tool_id: tools.mock
tool_version: "0.1.0"
env_id: bioimage-mcp-mock
entrypoint: mock_entrypoint.py
functions: []
"""
    manifest_path.write_text(manifest_content)

    manager = PersistentWorkerManager(manifest_roots=[tools_dir])

    entrypoint = manager._resolve_entrypoint("bioimage-mcp-mock")

    assert entrypoint.resolve() == entrypoint_path.resolve()
    assert entrypoint.exists()


def test_resolve_entrypoint_multiple_roots(tmp_path):
    """Test resolution with multiple manifest roots."""
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"

    # Tool in root1
    tool1_dir = root1 / "tool1"
    tool1_dir.mkdir(parents=True)
    (tool1_dir / "manifest.yaml").write_text(
        'env_id: bioimage-mcp-env1\nentrypoint: ep1.py\ntool_id: t1\nmanifest_version: "1.0"\ntool_version: "1"\nfunctions: []'
    )
    (tool1_dir / "ep1.py").write_text("")

    # Tool in root2
    tool2_dir = root2 / "tool2"
    tool2_dir.mkdir(parents=True)
    (tool2_dir / "manifest.yaml").write_text(
        'env_id: bioimage-mcp-env2\nentrypoint: ep2.py\ntool_id: t2\nmanifest_version: "1.0"\ntool_version: "1"\nfunctions: []'
    )
    (tool2_dir / "ep2.py").write_text("")

    manager = PersistentWorkerManager(manifest_roots=[root1, root2])

    ep1 = manager._resolve_entrypoint("bioimage-mcp-env1")
    assert ep1.name == "ep1.py"

    ep2 = manager._resolve_entrypoint("bioimage-mcp-env2")
    assert ep2.name == "ep2.py"
