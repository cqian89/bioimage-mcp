from __future__ import annotations

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

    # Default is OME-TIFF
    assert io_bridge.negotiate_format(ref) == "OME-TIFF"

    # Specific supported format
    assert io_bridge.negotiate_format(ref, target_required_format="OME-Zarr") == "OME-Zarr"

    # Fallback for unsupported format
    assert io_bridge.negotiate_format(ref, target_required_format="PNG") == "OME-TIFF"


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
    assert path_zarr == tmp_path / "session1" / "art2.zarr"


@pytest.mark.xfail(reason="T024: IOBridge not yet integrated with ExecutionBridge")
def test_cross_env_materialization_integration(io_bridge: IOBridge):
    """Test that the system automatically materializes cross-env handoffs.

    This requires ExecutionBridge integration (T024).
    """
    # This is a placeholder for the integration test that will be fully implemented in T024.
    # It should verify that when tool A (env1) produces a memory artifact
    # and tool B (env2) consumes it, the system:
    # 1. Detects the need for handoff via IOBridge
    # 2. Negotiates OME-TIFF
    # 3. Materializes the memory artifact to disk
    # 4. Updates Tool B's input to the new file-backed artifact
    # 5. Records the handoff in provenance

    raise NotImplementedError("T024 not yet implemented")
