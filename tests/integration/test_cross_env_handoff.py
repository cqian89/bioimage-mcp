from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.io_bridge import IOBridge, IOBridgeHandoff


@pytest.fixture
def io_bridge(tmp_path: Path) -> IOBridge:
    return IOBridge(artifact_store_path=tmp_path)


def test_io_bridge_needs_handoff(io_bridge: IOBridge):
    """Verify IOBridge detects when handoff is needed."""

    # Case 1: Same env, file-backed -> No handoff needed
    ref_file = ArtifactRef(
        ref_id="ref1",
        type="BioImageRef",
        uri="file:///path/to/image.ome.tiff",
        format="OME-TIFF",
        storage_type="file",
        mime_type="image/tiff",
        size_bytes=100,
        created_at=ArtifactRef.now(),
    )
    assert io_bridge.needs_handoff(ref_file, "env1", "env1") is False

    # Case 2: Different env, file-backed -> Handoff needed
    assert io_bridge.needs_handoff(ref_file, "env1", "env2") is True

    # Case 3: Same env, memory-backed -> Handoff needed (to materialize for tool)
    ref_mem = ArtifactRef(
        ref_id="ref2",
        type="BioImageRef",
        uri="mem://session1/env1/ref2",
        format="OME-TIFF",
        storage_type="memory",
        mime_type="image/tiff",
        size_bytes=100,
        created_at=ArtifactRef.now(),
    )
    assert io_bridge.needs_handoff(ref_mem, "env1", "env1") is True

    # Case 4: Different env, memory-backed -> Handoff needed
    assert io_bridge.needs_handoff(ref_mem, "env1", "env2") is True

    # Case 5: Same env, file-backed but format mismatch
    assert (
        io_bridge.needs_handoff(ref_file, "env1", "env1", target_required_format="OME-Zarr") is True
    )


def test_io_bridge_negotiate_format(io_bridge: IOBridge):
    """Verify IOBridge negotiates correct interchange formats."""
    ref = ArtifactRef(
        ref_id="ref1",
        type="BioImageRef",
        uri="file:///path/to/image.ome.tiff",
        format="OME-TIFF",
        storage_type="file",
        mime_type="image/tiff",
        size_bytes=100,
        created_at=ArtifactRef.now(),
    )

    # Default is OME-Zarr (T049)
    assert io_bridge.negotiate_format(ref) == "OME-Zarr"

    # Specific supported format
    assert io_bridge.negotiate_format(ref, target_required_format="OME-Zarr") == "OME-Zarr"

    # Fallback for unsupported format (T049: fallback to new default)
    assert io_bridge.negotiate_format(ref, target_required_format="PNG") == "OME-Zarr"


def test_io_bridge_record_handoff(io_bridge: IOBridge):
    """Verify IOBridge records handoff provenance."""
    handoff = io_bridge.record_handoff(
        source_ref_id="src1",
        target_ref_id="tgt1",
        source_env="env1",
        target_env="env2",
        format="OME-TIFF",
    )

    assert isinstance(handoff, IOBridgeHandoff)
    assert handoff.source_ref_id == "src1"
    assert handoff.target_ref_id == "tgt1"
    assert handoff.source_env == "env1"
    assert handoff.target_env == "env2"
    assert handoff.negotiated_format == "OME-TIFF"
    assert handoff.timestamp is not None

    history = io_bridge.get_handoff_history()
    assert len(history) == 1
    assert history[0] == handoff


def test_io_bridge_create_materialization_path(io_bridge: IOBridge, tmp_path: Path):
    """Verify materialization path generation."""
    path = io_bridge.create_materialization_path("session1", "art1", "OME-TIFF")
    assert path == tmp_path / "session1" / "art1.ome.tiff"

    path_zarr = io_bridge.create_materialization_path("session1", "art2", "OME-Zarr")
    assert path_zarr == tmp_path / "session1" / "art2.ome.zarr"


def _env_available(env_name: str) -> bool:
    try:
        proc = subprocess.run(
            ["conda", "run", "-n", env_name, "python", "-c", "print('ok')"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def test_cross_env_materialization_integration(tmp_path: Path):
    """Test that the system automatically materializes cross-env handoffs.

    Verified for T024.
    """
    if not _env_available("env-other"):
        pytest.skip("Required tool environment missing: env-other")

    import uuid

    from bioimage_mcp.api.execution import ExecutionService
    from bioimage_mcp.artifacts.memory import build_mem_uri
    from bioimage_mcp.config.schema import Config

    # Setup config and service
    config = Config(
        artifact_store_root=tmp_path,
        tool_manifest_roots=[Path("tools").absolute()],
    )
    with ExecutionService(config) as service:
        # 1. Create a simulated memory artifact from "env-other"
        session_id = "test-session"
        env_id_src = "env-other"
        ref_id_src = f"mem-{uuid.uuid4().hex[:8]}"
        uri_src = build_mem_uri(session_id, env_id_src, ref_id_src)

        # Create a real file to back the memory artifact (simulating T016 behavior)
        sim_path = tmp_path / "simulated.ome.tiff"
        import numpy as np
        from bioio.writers import OmeTiffWriter

        data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)
        OmeTiffWriter.save(data, str(sim_path), dim_order="TCZYX")

        ref_src = ArtifactRef(
            ref_id=ref_id_src,
            type="BioImageRef",
            uri=uri_src,
            format="OME-TIFF",
            storage_type="memory",
            mime_type="image/tiff",
            size_bytes=sim_path.stat().st_size,
            created_at=ArtifactRef.now(),
            metadata={"_simulated_path": str(sim_path)},
        )
        service._memory_store.register(ref_src)

        # 2. Run a tool in "bioimage-mcp-base" (different env) that consumes it
        # We'll use a simple base tool
        spec = {
            "steps": [
                {
                    "id": "base.xarray.rename",
                    "inputs": {"image": {"ref_id": ref_id_src}},
                    "params": {"mapping": {"Z": "T", "T": "Z"}},
                }
            ],
            "run_opts": {"session_id": session_id},
        }

        # Execute
        result = service.run_workflow(spec)
        assert result["status"] == "success"

        # 3. Verify handoff record in provenance
        run = service._run_store.get(result["run_id"])
        assert "handoffs" in run.provenance
        handoffs = run.provenance["handoffs"]
        assert len(handoffs) == 1
        handoff = handoffs[0]
        assert handoff["source_ref_id"] == ref_id_src
        assert handoff["source_env"] == env_id_src
        assert handoff["target_env"] == "bioimage-mcp-base"
        assert handoff["negotiated_format"] == "OME-Zarr"

        # 4. Verify that a new file-backed artifact was created
        materialized_ref_id = handoff["target_ref_id"]
        mat_ref = service._artifact_store.get(materialized_ref_id)
        assert mat_ref.storage_type == "file"
        assert Path(mat_ref.uri.replace("file://", "")).exists()
