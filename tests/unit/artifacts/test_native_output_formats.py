"""Unit tests for NativeOutputRef with various format values (T050).

Tests that ArtifactStore handles NativeOutputRef with different format values
correctly, supporting the open/extensible format field.
"""

from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.store import ArtifactStore, _guess_mime_type
from bioimage_mcp.config.schema import Config


class TestNativeOutputRefFormats:
    """Tests for NativeOutputRef with various format values."""

    def test_write_native_output_workflow_record_json(self, tmp_path: Path) -> None:
        """Test writing NativeOutputRef with workflow-record-json format."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        with ArtifactStore(config) as store:
            ref = store.write_native_output(
                {"key": "value"},
                format="workflow-record-json",
                metadata={"test": True},
            )

            assert ref.type == "NativeOutputRef"
            assert ref.format == "workflow-record-json"
            assert ref.mime_type == "application/json"
            assert ref.metadata["test"] is True

    def test_write_native_output_cellpose_seg_npy(self, tmp_path: Path) -> None:
        """Test writing NativeOutputRef with cellpose-seg-npy format."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        with ArtifactStore(config) as store:
            ref = store.write_native_output(
                b"binary data simulating npy",
                format="cellpose-seg-npy",
                metadata={"model": "cyto3"},
            )

            assert ref.type == "NativeOutputRef"
            assert ref.format == "cellpose-seg-npy"
            assert ref.mime_type == "application/x-npy"
            assert ref.metadata["model"] == "cyto3"

    def test_write_native_output_generic_format(self, tmp_path: Path) -> None:
        """Test writing NativeOutputRef with a generic/unknown format."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        with ArtifactStore(config) as store:
            ref = store.write_native_output(
                "some text content",
                format="custom-vendor-format",
            )

            assert ref.type == "NativeOutputRef"
            assert ref.format == "custom-vendor-format"
            # Should fallback to octet-stream for unknown formats
            assert ref.mime_type == "application/octet-stream"


class TestGuessMimeType:
    """Tests for _guess_mime_type helper function."""

    def test_log_ref_returns_text_plain(self) -> None:
        """LogRef always returns text/plain."""
        assert _guess_mime_type("LogRef", "text") == "text/plain"
        assert _guess_mime_type("LogRef", "json") == "text/plain"

    def test_ome_zarr_formats(self) -> None:
        """OME-Zarr and zarr formats return zarr MIME type."""
        assert _guess_mime_type("BioImageRef", "ome-zarr") == "application/zarr+ome"
        assert _guess_mime_type("BioImageRef", "zarr") == "application/zarr+ome"
        assert _guess_mime_type("BioImageRef", "OME-Zarr") == "application/zarr+ome"

    def test_tiff_formats(self) -> None:
        """TIFF formats return image/tiff."""
        assert _guess_mime_type("BioImageRef", "ome-tiff") == "image/tiff"
        assert _guess_mime_type("BioImageRef", "tiff") == "image/tiff"
        assert _guess_mime_type("LabelImageRef", "tif") == "image/tiff"

    def test_native_output_json_format(self) -> None:
        """NativeOutputRef with JSON hint returns application/json."""
        assert _guess_mime_type("NativeOutputRef", "workflow-record-json") == "application/json"
        assert _guess_mime_type("NativeOutputRef", "some-json-thing") == "application/json"

    def test_native_output_npy_format(self) -> None:
        """NativeOutputRef with npy hint returns application/x-npy."""
        assert _guess_mime_type("NativeOutputRef", "cellpose-seg-npy") == "application/x-npy"
        assert _guess_mime_type("NativeOutputRef", "numpy-array-npy") == "application/x-npy"

    def test_unknown_format_fallback(self) -> None:
        """Unknown formats fallback to application/octet-stream."""
        assert _guess_mime_type("BioImageRef", "unknown-format") == "application/octet-stream"
        assert _guess_mime_type("NativeOutputRef", "custom-vendor") == "application/octet-stream"
