import pytest
from bioimage_mcp.api.schemas import DimensionRequirement, InputRequirement


def test_dimension_requirements_parsing():
    # Simulate a manifest fragment
    data = {
        "min_ndim": 2,
        "max_ndim": 3,
        "expected_axes": ["Y", "X"],
        "preprocessing_instructions": ["Squeeze singleton T, C, Z dimensions if present"],
    }

    req = DimensionRequirement(**data)
    assert req.min_ndim == 2
    assert req.max_ndim == 3
    assert req.expected_axes == ["Y", "X"]
    assert req.preprocessing_instructions == ["Squeeze singleton T, C, Z dimensions if present"]


def test_input_requirement_with_dimensions():
    data = {
        "name": "image",
        "type": "BioImageRef",
        "required": True,
        "description": "test image",
        "dimension_requirements": {"min_ndim": 5, "expected_axes": ["T", "C", "Z", "Y", "X"]},
    }

    input_req = InputRequirement(**data)

    assert input_req.dimension_requirements is not None
    assert input_req.dimension_requirements.min_ndim == 5
    assert input_req.dimension_requirements.expected_axes == ["T", "C", "Z", "Y", "X"]
