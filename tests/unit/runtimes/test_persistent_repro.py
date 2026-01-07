from pathlib import Path

from bioimage_mcp.runtimes.persistent import PersistentWorkerManager


def test_worker_entrypoint_resolution_from_manifest(tmp_path):
    """
    Verify that PersistentWorkerManager can resolve the entrypoint from the manifest
    when provided with manifest roots.
    """
    # Create a mock manifest
    tool_dir = tmp_path / "tools" / "mock_tool"
    tool_dir.mkdir(parents=True)

    manifest_path = tool_dir / "manifest.yaml"
    entrypoint_rel_path = "subdir/entrypoint.py"
    entrypoint_abs_path = tool_dir / entrypoint_rel_path
    entrypoint_abs_path.parent.mkdir(parents=True)
    entrypoint_abs_path.write_text("print('hello')")

    manifest_content = f"""
manifest_version: "1.0"
tool_id: tools.mock
tool_version: "0.1.0"
env_id: bioimage-mcp-mock
entrypoint: {entrypoint_rel_path}
functions: []
"""
    manifest_path.write_text(manifest_content)

    # Initialize manager with manifest roots
    manager = PersistentWorkerManager(manifest_roots=[tmp_path / "tools"])

    entrypoint = manager._resolve_entrypoint("bioimage-mcp-mock")
    assert entrypoint.resolve() == entrypoint_abs_path.resolve()


def test_cellpose_worker_resolved_correctly():
    """
    Verify that cellpose worker entrypoint is resolved correctly when manifest roots are provided.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    manager = PersistentWorkerManager(manifest_roots=[repo_root / "tools"])

    # Resolve the entrypoint without spawning
    entrypoint = manager._resolve_entrypoint("bioimage-mcp-cellpose")

    expected_entrypoint = (
        repo_root / "tools" / "cellpose" / "bioimage_mcp_cellpose" / "entrypoint.py"
    )
    assert entrypoint.resolve() == expected_entrypoint.resolve()


def test_base_worker_resolved_correctly():
    """
    Verify that base worker entrypoint is resolved correctly.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    manager = PersistentWorkerManager(manifest_roots=[repo_root / "tools"])

    # Resolve the entrypoint without spawning
    entrypoint = manager._resolve_entrypoint("bioimage-mcp-base")

    expected_entrypoint = repo_root / "tools" / "base" / "bioimage_mcp_base" / "entrypoint.py"
    assert entrypoint.resolve() == expected_entrypoint.resolve()
