from bioimage_mcp.artifacts.models import ArtifactRef


def test_artifactref_excludes_none_fields():
    """Verify that None fields are NOT serialized in model_dump()."""
    ref = ArtifactRef(
        ref_id="test-1",
        type="BioImageRef",
        uri="file:///tmp/test.tif",
        format=None,
        mime_type=None,
    )
    dump = ref.model_dump()
    # These should FAIL currently
    assert "format" not in dump
    assert "mime_type" not in dump
    assert "size_bytes" not in dump
    assert "schema_version" not in dump


def test_artifactref_excludes_empty_checksums():
    """Verify that empty checksums list is excluded from model_dump()."""
    ref = ArtifactRef(ref_id="test-1", type="BioImageRef", uri="file:///tmp/test.tif", checksums=[])
    dump = ref.model_dump()
    # Should FAIL currently
    assert "checksums" not in dump


def test_artifactref_no_toplevel_dims_fields():
    """Verify top-level dimension fields don't exist on ArtifactRef."""
    toplevel_dims = ["ndim", "dims", "shape", "dtype", "physical_pixel_sizes"]

    # Should FAIL currently because they ARE in the fields
    for field in toplevel_dims:
        assert field not in ArtifactRef.model_fields, (
            f"Field {field} should not be in ArtifactRef.model_fields"
        )


def test_artifactref_dims_in_metadata_only():
    """Verify dimension data lives in metadata and is NOT at top level in dump."""
    metadata = {
        "ndim": 3,
        "dims": ["Z", "Y", "X"],
        "shape": [10, 512, 512],
        "dtype": "uint16",
        "physical_pixel_sizes": {"X": 0.1, "Y": 0.1, "Z": 0.5},
    }
    ref = ArtifactRef(
        ref_id="test-1", type="BioImageRef", uri="file:///tmp/test.tif", metadata=metadata
    )

    dump = ref.model_dump()
    assert dump["metadata"]["ndim"] == 3

    # These should FAIL currently because they are currently defined at top level
    assert "ndim" not in dump
    assert "dims" not in dump
    assert "shape" not in dump
    assert "dtype" not in dump
    assert "physical_pixel_sizes" not in dump


def test_artifactref_excludes_empty_metadata():
    """Verify empty metadata dict is excluded from model_dump()."""
    ref = ArtifactRef(ref_id="test-1", type="BioImageRef", uri="file:///tmp/test.tif", metadata={})
    dump = ref.model_dump()
    # Should FAIL currently
    assert "metadata" not in dump
