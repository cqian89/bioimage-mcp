import pytest

from bioimage_mcp.api.serializers import RunResponseSerializer


@pytest.fixture
def sample_artifact_ref():
    """Sample artifact reference for testing."""
    return {
        "ref_id": "art_123",
        "type": "BioImageRef",
        "uri": "file:///path/to/image.ome.tif",
        "format": "ome-tiff",
        "storage_type": "filesystem",
        "size_bytes": 1048576,  # 1.0 MB
        "shape": [1, 1, 10, 512, 512],
        "dims": "TCZYX",
        "dtype": "uint16",
        "physical_pixel_sizes": [1.0, 0.5, 0.5],
        "channel_names": ["DAPI", "GFP", "RFP"],
        "checksums": {"sha256": "abc123"},
        "created_at": "2026-01-13T10:00:00Z",
        "metadata": {"key": "value", "file_metadata": {"original_filename": "raw.tif"}},
        "workflow_record": {"step": 1},
    }


@pytest.fixture
def memory_artifact_ref():
    """Sample memory-backed artifact reference."""
    return {
        "ref_id": "mem_456",
        "type": "ObjectRef",
        "uri": "obj://cellpose_model_123",
        "storage_type": "memory",
        "size_bytes": 524288,  # 0.5 MB
        "python_class": "cellpose.models.CellposeModel",
    }


@pytest.fixture
def success_result(sample_artifact_ref):
    """Sample successful run result."""
    return {
        "run_id": "run_789",
        "session_id": "sess_000",
        "status": "success",
        "outputs": {"image": sample_artifact_ref},
        "warnings": [],
        "log_ref": {"ref_id": "log_111", "uri": "file:///logs/run_789.log"},
        "workflow_record": {"ref_id": "wf_123", "type": "NativeOutputRef"},
    }


@pytest.fixture
def failed_result():
    """Sample failed run result."""
    return {
        "run_id": "run_failed",
        "session_id": "sess_000",
        "status": "failed",
        "outputs": {},
        "warnings": ["Low memory warning"],
        "log_ref": {"ref_id": "log_222", "uri": "file:///logs/run_failed.log"},
    }


class TestRunResponseSerializer:
    """Unit tests for RunResponseSerializer."""

    def test_serialize_minimal_success(self, success_result):
        """Test minimal verbosity for a successful run."""
        serializer = RunResponseSerializer()
        serialized = serializer.serialize(success_result, fn_id="base.gauss", verbosity="minimal")

        # Top-level fields
        assert "run_id" in serialized
        assert "status" in serialized
        assert "fn_id" in serialized
        assert "outputs" in serialized
        assert "session_id" not in serialized
        assert "warnings" not in serialized  # Empty warnings should be excluded
        assert "log_ref" not in serialized  # Success log_ref should be excluded in minimal

        # Artifact fields
        artifact = serialized["outputs"]["image"]
        assert artifact["ref_id"] == "art_123"
        assert artifact["type"] == "BioImageRef"
        assert artifact["shape"] == [1, 1, 10, 512, 512]
        assert artifact["dims"] == ["T", "C", "Z", "Y", "X"]
        assert artifact["dtype"] == "uint16"
        assert artifact["size_mb"] == 1.0

        # Optional fields allowed in minimal
        assert artifact["physical_pixel_sizes"] == [1.0, 0.5, 0.5]
        assert artifact["format"] == "ome-tiff"
        assert artifact["channel_names"] == ["DAPI", "GFP", "RFP"]

        # Fields that should be excluded in minimal (except uri)
        assert artifact["uri"] == "file:///path/to/image.ome.tif"
        assert "storage_type" not in artifact
        assert "size_bytes" not in artifact
        assert "metadata" not in artifact
        assert "checksums" not in artifact
        assert "created_at" not in artifact
        assert "workflow_record" not in artifact

    def test_serialize_minimal_memory_artifact(self, memory_artifact_ref):
        """Test that artifacts include URI in minimal mode."""
        result = {
            "run_id": "run_mem",
            "status": "success",
            "outputs": {"model": memory_artifact_ref},
        }
        serializer = RunResponseSerializer()
        serialized = serializer.serialize(result, fn_id="cellpose.train", verbosity="minimal")

        artifact = serialized["outputs"]["model"]
        assert artifact["uri"] == "obj://cellpose_model_123"

    def test_serialize_minimal_failed(self, failed_result):
        """Test minimal verbosity for a failed run."""
        serializer = RunResponseSerializer()
        serialized = serializer.serialize(failed_result, fn_id="base.gauss", verbosity="minimal")

        assert serialized["status"] == "failed"
        assert "warnings" in serialized
        assert serialized["warnings"] == ["Low memory warning"]
        assert "log_ref" in serialized  # Failed runs always include log_ref

    def test_serialize_standard_success(self, success_result):
        """Test standard verbosity level."""
        serializer = RunResponseSerializer()
        serialized = serializer.serialize(success_result, fn_id="base.gauss", verbosity="standard")

        artifact = serialized["outputs"]["image"]
        assert "uri" in artifact
        assert artifact["uri"] == "file:///path/to/image.ome.tif"
        assert artifact["storage_type"] == "filesystem"
        assert artifact["size_bytes"] == 1048576
        assert artifact["size_mb"] == 1.0
        assert "metadata" in artifact
        assert artifact["metadata"]["key"] == "value"

        # Exclusions in standard
        assert "checksums" not in artifact
        assert "created_at" not in artifact
        assert "file_metadata" not in artifact["metadata"]

    def test_serialize_full_success(self, success_result):
        """Test full verbosity level."""
        serializer = RunResponseSerializer()
        serialized = serializer.serialize(success_result, fn_id="base.gauss", verbosity="full")

        assert "log_ref" in serialized
        assert "workflow_record" in serialized
        artifact = serialized["outputs"]["image"]
        assert "checksums" in artifact
        assert "created_at" in artifact
        assert "file_metadata" in artifact["metadata"]
        assert "workflow_record" in artifact

    def test_invalid_verbosity_coerced_to_minimal(self, success_result, caplog):
        """Test that invalid verbosity is coerced to minimal with a warning."""
        serializer = RunResponseSerializer()
        with caplog.at_level("WARNING"):
            serialized = serializer.serialize(
                success_result, fn_id="base.gauss", verbosity="invalid"
            )

        assert "Invalid verbosity 'invalid', coercing to 'minimal'" in caplog.text
        # Should match minimal output
        assert serialized["outputs"]["image"]["uri"] == "file:///path/to/image.ome.tif"
        assert "storage_type" not in serialized["outputs"]["image"]

    def test_extract_from_metadata_priority(self):
        """Test that dimension fields are extracted from metadata with priority."""
        artifact = {
            "ref_id": "art_1",
            "type": "BioImageRef",
            "shape": [1, 1, 1, 10, 10],  # Top-level
            "metadata": {
                "shape": [1, 1, 1, 20, 20],  # Metadata (higher priority)
                "dims": "ZYX",
            },
            "summary": {
                "dims": "TCZYX"  # Summary (lower priority)
            },
        }
        result = {"run_id": "run_1", "status": "success", "outputs": {"image": artifact}}
        serializer = RunResponseSerializer()
        serialized = serializer.serialize(result, fn_id="test", verbosity="minimal")

        out = serialized["outputs"]["image"]
        assert out["shape"] == [1, 1, 1, 20, 20]
        assert out["dims"] == ["Z", "Y", "X"]

    def test_filter_workflow_record_from_outputs(self, success_result):
        """Test that 'workflow_record' key in outputs is filtered unless full verbosity."""
        success_result["outputs"]["workflow_record"] = {
            "ref_id": "wf_out",
            "type": "NativeOutputRef",
        }

        serializer = RunResponseSerializer()

        # Minimal: should be filtered
        serialized_min = serializer.serialize(success_result, fn_id="test", verbosity="minimal")
        assert "workflow_record" not in serialized_min["outputs"]

        # Standard: should be filtered
        serialized_std = serializer.serialize(success_result, fn_id="test", verbosity="standard")
        assert "workflow_record" not in serialized_std["outputs"]

        # Full: should be included
        serialized_full = serializer.serialize(success_result, fn_id="test", verbosity="full")
        assert "workflow_record" in serialized_full["outputs"]

    def test_sanitize_artifact_removes_summary_and_content(self):
        """Test that 'summary' and 'content' are removed from artifacts in all verbosities."""
        artifact = {
            "ref_id": "art_1",
            "type": "LogRef",
            "summary": "Process completed",
            "content": "Line 1\nLine 2",
            "metadata": {"foo": "bar"},
        }
        result = {"run_id": "run_1", "status": "success", "outputs": {"log": artifact}}
        serializer = RunResponseSerializer()

        for verbosity in ["minimal", "standard", "full"]:
            serialized = serializer.serialize(result, fn_id="test", verbosity=verbosity)
            out = serialized["outputs"]["log"]
            assert "summary" not in out
            assert "content" not in out

    def test_error_status_always_includes_log_ref(self):
        """Test that validation_failed always includes log_ref."""
        result = {
            "run_id": "run_val_fail",
            "status": "validation_failed",
            "outputs": {},
            "log_ref": {"ref_id": "log_val", "uri": "file:///logs/val.log"},
        }
        serializer = RunResponseSerializer()

        # Even with minimal verbosity
        serialized = serializer.serialize(result, fn_id="base.gauss", verbosity="minimal")
        assert "log_ref" in serialized

    def test_size_mb_helper(self):
        """Test the _size_mb helper method."""
        serializer = RunResponseSerializer()
        assert serializer._size_mb(1048576) == 1.0
        assert serializer._size_mb(524288) == 0.5
        assert serializer._size_mb(0) == 0.0
        assert serializer._size_mb(1500000) == 1.43  # Rounded to 2 decimal places

    def test_maybe_truncate_channel_names_helper(self):
        """Test the channel name truncation helper."""
        serializer = RunResponseSerializer()

        # No truncation needed
        names = [f"Ch{i}" for i in range(5)]
        assert serializer._maybe_truncate_channel_names(names) == names

        # Truncation needed
        names = [f"Ch{i}" for i in range(15)]
        truncated = serializer._maybe_truncate_channel_names(names)
        assert len(truncated) == 11
        assert truncated[10] == "...+5 more"
        assert truncated[:10] == names[:10]

    def test_channel_names_truncation_in_serialization(self, success_result):
        """Test that channel names are truncated during serialization in minimal mode."""
        success_result["outputs"]["image"]["channel_names"] = [f"Ch{i}" for i in range(12)]

        serializer = RunResponseSerializer()
        serialized = serializer.serialize(success_result, fn_id="base.gauss", verbosity="minimal")

        artifact = serialized["outputs"]["image"]
        assert len(artifact["channel_names"]) == 11
        assert artifact["channel_names"][10] == "...+2 more"
