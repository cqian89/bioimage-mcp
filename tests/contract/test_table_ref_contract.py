from __future__ import annotations

import pytest
from bioimage_mcp.artifacts.models import ArtifactRef, TableRef


def test_table_ref_creation() -> None:
    # This should fail if TableRef is not defined
    ref = TableRef(
        ref_id="table-1",
        type="TableRef",
        uri="file:///tmp/table.parquet",
        format="parquet",
        mime_type="application/x-parquet",
        size_bytes=1024,
        created_at="2025-01-01T00:00:00Z",
        metadata={
            "columns": [{"name": "area", "dtype": "float64"}, {"name": "label", "dtype": "int64"}],
            "row_count": 100,
        },
    )
    assert ref.type == "TableRef"
    assert "columns" in ref.metadata
    assert len(ref.metadata["columns"]) == 2
    assert ref.metadata["row_count"] == 100
    assert ref.metadata["columns"][0]["name"] == "area"


def test_table_ref_metadata_validation() -> None:
    # If we have TableRef specific class or validation in ArtifactRef
    # For now, let's just assert that we expect these fields
    pass
