from __future__ import annotations

import pytest
from pydantic import ValidationError
from bioimage_mcp.artifacts.models import ScalarRef


def test_scalar_ref_creation() -> None:
    # This should fail if ScalarRef is not defined
    ref = ScalarRef(
        ref_id="scalar-1",
        type="ScalarRef",
        uri="file:///tmp/scalar.json",
        format="json",
        mime_type="application/json",
        size_bytes=123,
        created_at="2025-01-01T00:00:00Z",
        metadata={"value": 42.0, "dtype": "float64", "unit": "um"},
    )
    assert ref.type == "ScalarRef"
    assert ref.format == "json"
    assert ref.metadata["value"] == 42.0


def test_scalar_ref_requires_metadata_fields() -> None:
    # ScalarMetadata should require value and dtype
    with pytest.raises(ValidationError):
        ScalarRef(
            ref_id="scalar-1",
            type="ScalarRef",
            uri="file:///tmp/scalar.json",
            format="json",
            mime_type="application/json",
            size_bytes=123,
            created_at="2025-01-01T00:00:00Z",
            metadata={"unit": "um"},
        )
