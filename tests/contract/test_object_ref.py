from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_object_ref_schema_validation():
    """T004: Test ObjectRef schema validation with required and optional fields."""
    # This import should fail until ObjectRef is implemented
    from bioimage_mcp.artifacts.models import ObjectRef

    # Test valid ObjectRef
    obj_ref = ObjectRef(
        ref_id="model_123",
        type="ObjectRef",
        uri="obj://session_1/env_1/model_123",
        format="pickle",
        python_class="cellpose.models.CellposeModel",
        storage_type="memory",
        metadata={
            "device": "cuda",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    )

    assert obj_ref.ref_id == "model_123"
    assert obj_ref.type == "ObjectRef"
    assert obj_ref.uri == "obj://session_1/env_1/model_123"
    assert obj_ref.format == "pickle"
    assert obj_ref.python_class == "cellpose.models.CellposeModel"
    assert obj_ref.storage_type == "memory"
    assert obj_ref.metadata["device"] == "cuda"
    assert "init_params" not in obj_ref.metadata


def test_object_ref_required_fields():
    """T004: Test ObjectRef missing required fields."""
    from bioimage_mcp.artifacts.models import ObjectRef

    # Missing ref_id
    with pytest.raises(ValidationError):
        ObjectRef(
            type="ObjectRef",
            uri="obj://s/e/o",
            format="pickle",
            python_class="MyClass",
            storage_type="memory",
        )

    # Missing python_class
    with pytest.raises(ValidationError):
        ObjectRef(
            ref_id="o1",
            type="ObjectRef",
            uri="obj://s/e/o",
            format="pickle",
            storage_type="memory",
        )


def test_object_ref_uri_validation():
    """T005: Test ObjectRef URI validation (obj:// scheme)."""
    from bioimage_mcp.artifacts.models import ObjectRef

    # Valid URI
    ObjectRef(
        ref_id="o1",
        type="ObjectRef",
        uri="obj://session-123/env-456/obj-789",
        format="pickle",
        python_class="MyClass",
        storage_type="memory",
    )

    # Invalid scheme
    with pytest.raises(ValidationError, match="must have an obj:// URI"):
        ObjectRef(
            ref_id="o1",
            type="ObjectRef",
            uri="mem://session/env/obj",
            format="pickle",
            python_class="MyClass",
            storage_type="memory",
        )

    # Invalid format (missing parts)
    with pytest.raises(ValidationError, match="Invalid object URI format"):
        ObjectRef(
            ref_id="o1",
            type="ObjectRef",
            uri="obj://session",
            format="pickle",
            python_class="MyClass",
            storage_type="memory",
        )
