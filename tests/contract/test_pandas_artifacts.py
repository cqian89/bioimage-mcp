from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioimage_mcp.artifacts.models import (
    GroupByRef,
    ObjectRef,
    TableRef,
)


def test_table_ref_pandas_contract() -> None:
    """T005: Validate TableRef schema for pandas artifacts."""
    # Test with all fields from the specification
    table_data = {
        "ref_id": "table-123",
        "type": "TableRef",
        "uri": "file:///path/to/table.csv",
        "format": "csv",
        "columns": ["id", "area", "intensity", "label"],
        "row_count": 1250,
        "delimiter": ",",
        "schema_id": "bioimage.schema.measurements.v1",
        "metadata": {
            "columns": [
                {"name": "id", "dtype": "int64"},
                {"name": "area", "dtype": "float64"},
                {"name": "intensity", "dtype": "float64"},
                {"name": "label", "dtype": "int64"},
            ],
            "row_count": 1250,
            "delimiter": ",",
        },
    }

    ref = TableRef(**table_data)
    assert ref.type == "TableRef"
    assert ref.columns == ["id", "area", "intensity", "label"]
    assert ref.row_count == 1250
    assert ref.delimiter == ","
    assert ref.schema_id == "bioimage.schema.measurements.v1"
    assert len(ref.metadata.columns) == 4


def test_table_ref_required_fields() -> None:
    """T005: Test TableRef missing required fields."""
    # Missing columns
    with pytest.raises(ValidationError):
        TableRef(
            ref_id="t1",
            type="TableRef",
            uri="file:///t.csv",
            row_count=10,
            metadata={"columns": [], "row_count": 10},
        )

    # Missing row_count
    with pytest.raises(ValidationError):
        TableRef(
            ref_id="t1",
            type="TableRef",
            uri="file:///t.csv",
            columns=["a"],
            metadata={"columns": [], "row_count": 10},
        )


def test_object_ref_pandas_contract() -> None:
    """T005: Validate ObjectRef schema for pandas DataFrames."""
    obj_data = {
        "ref_id": "df-123",
        "type": "ObjectRef",
        "uri": "obj://pandas.DataFrame/uuid-1234",
        "python_class": "pandas.core.frame.DataFrame",
        "storage_type": "memory",
        "metadata": {"columns": ["id", "area"], "shape": [1250, 2]},
    }

    ref = ObjectRef(**obj_data)
    assert ref.type == "ObjectRef"
    assert ref.python_class == "pandas.core.frame.DataFrame"
    assert ref.storage_type == "memory"
    assert ref.metadata["columns"] == ["id", "area"]
    assert ref.metadata["shape"] == [1250, 2]


def test_groupby_ref_pandas_contract() -> None:
    """T005: Validate GroupByRef schema."""
    groupby_data = {
        "ref_id": "gb-123",
        "type": "GroupByRef",
        "uri": "obj://pandas.core.groupby.DataFrameGroupBy/uuid-5678",
        "python_class": "pandas.core.groupby.generic.DataFrameGroupBy",
        "storage_type": "memory",
        "metadata": {"grouped_by": ["label"], "groups_count": 5},
    }

    ref = GroupByRef(**groupby_data)
    assert ref.type == "GroupByRef"
    assert ref.metadata.grouped_by == ["label"]
    assert ref.metadata.groups_count == 5


def test_groupby_ref_required_metadata() -> None:
    """T005: Test GroupByRef missing required metadata fields."""
    # Missing grouped_by in metadata
    with pytest.raises(ValidationError):
        GroupByRef(
            ref_id="gb-1",
            type="GroupByRef",
            uri="obj://p/g",
            python_class="pandas.GroupBy",
            storage_type="memory",
            metadata={"groups_count": 5},  # type: ignore
        )

    # Missing groups_count in metadata
    with pytest.raises(ValidationError):
        GroupByRef(
            ref_id="gb-1",
            type="GroupByRef",
            uri="obj://p/g",
            python_class="pandas.GroupBy",
            storage_type="memory",
            metadata={"grouped_by": ["label"]},  # type: ignore
        )
