from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_create_memory_artifact_ref_dims(tmp_path):
    config = Config(artifact_store_root=tmp_path, tool_manifest_roots=[])
    store = ArtifactStore(config)

    session_id = "test-session"
    env_id = "test-env"
    artifact_id = "test-art"

    # 3D data: ZYX
    shape = (10, 256, 256)
    dims = ["Z", "Y", "X"]

    # This should fail because create_memory_artifact_ref doesn't exist yet
    ref = store.create_memory_artifact_ref(
        session_id=session_id,
        env_id=env_id,
        artifact_id=artifact_id,
        artifact_type="BioImageRef",
        format="numpy",
        shape=shape,
        dims=dims,
        dtype="uint8",
    )

    assert ref.uri == f"mem://{session_id}/{env_id}/{artifact_id}"
    assert ref.storage_type == "memory"
    assert ref.ndim == 3
    assert ref.dims == ["Z", "Y", "X"]
    assert ref.metadata["shape"] == [10, 256, 256]
    assert ref.metadata["ndim"] == 3
    assert ref.metadata["dims"] == ["Z", "Y", "X"]
    assert ref.metadata["dtype"] == "uint8"
