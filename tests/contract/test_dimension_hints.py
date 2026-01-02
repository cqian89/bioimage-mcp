"""Contract tests for dimension hints in describe_function."""

from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter


class TestDimensionHintsContract:
    """Contract: dimension hints are returned correctly."""

    def test_skimage_gaussian_has_dimension_hints(self):
        """gaussian function returns dimension_requirements in hints."""
        adapter = SkimageAdapter()
        metadata = adapter.discover({"modules": ["skimage.filters"]})
        gaussian = next((m for m in metadata if m.name == "gaussian"), None)

        assert gaussian is not None
        assert gaussian.hints is not None
        assert "image" in gaussian.hints.inputs

        dim_req = gaussian.hints.inputs["image"].dimension_requirements
        assert dim_req is not None
        assert dim_req.max_ndim == 3  # 2D or 3D
        assert dim_req.preprocessing_instructions is not None

    def test_skimage_threshold_otsu_2d_only(self):
        """threshold_otsu requires 2D input."""
        adapter = SkimageAdapter()
        metadata = adapter.discover({"modules": ["skimage.filters"]})
        threshold_otsu = next((m for m in metadata if m.name == "threshold_otsu"), None)

        assert threshold_otsu is not None
        assert threshold_otsu.hints is not None

        dim_req = threshold_otsu.hints.inputs["image"].dimension_requirements
        assert dim_req.max_ndim == 2  # 2D only
        assert dim_req.min_ndim == 2

    def test_unknown_function_has_no_dimension_hints(self):
        """Unknown functions don't have dimension requirements."""
        adapter = SkimageAdapter()
        hint = adapter.generate_dimension_hints("skimage.some_module", "unknown_func")
        assert hint is None

    def test_dimension_requirements_has_preprocessing_instructions(self):
        """DimensionRequirement includes preprocessing_instructions."""
        adapter = SkimageAdapter()
        hint = adapter.generate_dimension_hints("skimage.segmentation", "felzenszwalb")

        assert hint is not None
        assert hint.preprocessing_instructions is not None
        assert len(hint.preprocessing_instructions) > 0
        assert any("squeeze" in s.lower() for s in hint.preprocessing_instructions)
