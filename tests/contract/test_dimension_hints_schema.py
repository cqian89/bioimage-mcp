from bioimage_mcp.api.schemas import DimensionRequirement, InputRequirement


def test_dimension_requirement_model_fields():
    """DimensionRequirement has all required fields."""
    req = DimensionRequirement(
        min_ndim=2,
        max_ndim=3,
        expected_axes=["Y", "X"],
        spatial_axes=["Y", "X"],
        squeeze_singleton=False,
        slice_strategy="max_intensity",
        preprocessing_instructions=["Convert to grayscale"],
    )
    assert req.min_ndim == 2
    assert req.max_ndim == 3
    assert req.expected_axes == ["Y", "X"]
    assert req.spatial_axes == ["Y", "X"]
    assert req.squeeze_singleton is False
    assert req.slice_strategy == "max_intensity"
    assert req.preprocessing_instructions == ["Convert to grayscale"]


def test_dimension_requirement_defaults():
    """DimensionRequirement has sensible defaults."""
    req = DimensionRequirement()
    assert req.min_ndim is None
    assert req.max_ndim is None
    assert req.expected_axes is None
    assert req.spatial_axes == ["Y", "X"]
    assert req.squeeze_singleton is True
    assert req.slice_strategy is None
    assert req.preprocessing_instructions is None


def test_input_requirement_includes_dimension_requirements():
    """InputRequirement has dimension_requirements field."""
    req = InputRequirement(
        type="BioImageRef",
        required=True,
        description="Test input",
        dimension_requirements=DimensionRequirement(min_ndim=2),
    )
    assert req.dimension_requirements is not None
    assert req.dimension_requirements.min_ndim == 2


def test_dimension_requirement_serialization():
    """DimensionRequirement can be serialized to JSON."""
    req = DimensionRequirement(min_ndim=2, expected_axes=["Y", "X"])
    data = req.model_dump()
    assert data["min_ndim"] == 2
    assert data["expected_axes"] == ["Y", "X"]
    assert data["spatial_axes"] == ["Y", "X"]
    assert data["squeeze_singleton"] is True
