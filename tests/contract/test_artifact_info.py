"""Contract tests for the 'artifact_info' MCP tool.

Verifies retrieval of artifact metadata and text previews.
"""

import json
from pathlib import Path
import pytest
from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


@pytest.fixture
def artifacts_svc(tmp_path: Path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
    )
    store = ArtifactStore(config)
    return ArtifactsService(store)


# T073: Metadata retrieval
def test_artifact_info_returns_metadata(artifacts_svc: ArtifactsService):
    """artifact_info should return basic metadata."""
    # Given: A stored artifact
    ref = artifacts_svc._store.write_log("test content")

    # When: artifact_info is called
    response = artifacts_svc.artifact_info(ref.ref_id)

    # Then: Response has basic metadata
    assert response["ref_id"] == ref.ref_id
    assert response["type"] == "LogRef"
    assert response["uri"] == ref.uri
    assert response["mime_type"] == "text/plain"
    assert response["size_bytes"] == len("test content")


# T074: Text preview
def test_artifact_info_text_preview(artifacts_svc: ArtifactsService):
    """artifact_info with text_preview_bytes should return preview."""
    # Given: A log artifact with some content
    content = "line1\nline2\nline3\nline4"
    ref = artifacts_svc._store.write_log(content)

    # When: artifact_info is called with text_preview_bytes
    response = artifacts_svc.artifact_info(ref.ref_id, text_preview_bytes=10)

    # Then: text_preview contains truncated log content
    assert response["text_preview"] == content[:10]


# T075: Checksums
def test_artifact_info_includes_checksums(artifacts_svc: ArtifactsService):
    """artifact_info should include checksums for verification."""
    # Given: A stored artifact
    ref = artifacts_svc._store.write_log("checksum test")

    # When: artifact_info is called
    response = artifacts_svc.artifact_info(ref.ref_id)

    # Then: checksums list contains algorithm and value
    assert len(response["checksums"]) > 0
    assert response["checksums"][0]["algorithm"] == "sha256"
    assert "value" in response["checksums"][0]


# T076: NOT_FOUND error
def test_artifact_info_not_found(artifacts_svc: ArtifactsService):
    """artifact_info should return NOT_FOUND for invalid ref_id."""
    # When: artifact_info is called with invalid ref_id
    response = artifacts_svc.artifact_info("invalid_ref")

    # Then: Error with code NOT_FOUND and details
    assert "error" in response
    assert response["error"]["code"] == "NOT_FOUND"
    assert "details" in response["error"]
    assert len(response["error"]["details"]) == 1
    assert response["error"]["details"][0]["path"] == "/ref_id"
    assert response["error"]["details"][0]["hint"] != ""


# T077: Image metadata
def test_artifact_info_image_metadata(artifacts_svc: ArtifactsService, tmp_path: Path):
    """artifact_info for images should include dims, dtype, shape."""
    # Given: A BioImageRef artifact
    # We'll mock the import_file or use a dummy file
    img_path = tmp_path / "test.tif"
    img_path.write_text("dummy tiff content")

    # Mocking metadata extraction since we don't have a real TIFF
    metadata_override = {
        "dims": ["Z", "Y", "X"],
        "ndim": 3,
        "shape": [10, 256, 256],
        "dtype": "uint16",
    }
    ref = artifacts_svc._store.import_file(
        img_path,
        artifact_type="BioImageRef",
        format="OME-TIFF",
        metadata_override=metadata_override,
    )

    # When: artifact_info is called
    response = artifacts_svc.artifact_info(ref.ref_id)

    # Then: Response has dims, ndim, dtype, shape
    assert response["dims"] == ["Z", "Y", "X"]
    assert response["ndim"] == 3
    assert response["dtype"] == "uint16"
    assert response["shape"] == [10, 256, 256]
