from bioimage_mcp.api.schemas import DimensionRequirement
from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter


def test_generate_dimension_hints_threshold_2d():
    """Threshold functions require 2D input."""
    adapter = SkimageAdapter()
    hints = adapter.generate_dimension_hints("skimage.filters", "threshold_otsu")

    assert isinstance(hints, DimensionRequirement)
    assert hints.min_ndim == 2
    assert hints.max_ndim == 2
    assert hints.expected_axes == ["Y", "X"]
    assert hints.squeeze_singleton is True
    assert any("Squeeze singleton" in instr for instr in hints.preprocessing_instructions)


def test_generate_dimension_hints_felzenszwalb_2d():
    """felzenszwalb requires 2D input."""
    adapter = SkimageAdapter()
    hints = adapter.generate_dimension_hints("skimage.segmentation", "felzenszwalb")

    assert isinstance(hints, DimensionRequirement)
    assert hints.min_ndim == 2
    assert hints.max_ndim == 2
    assert hints.expected_axes == ["Y", "X"]


def test_generate_dimension_hints_gaussian_2d_or_3d():
    """gaussian supports 2D or 3D."""
    adapter = SkimageAdapter()
    hints = adapter.generate_dimension_hints("skimage.filters", "gaussian")

    assert isinstance(hints, DimensionRequirement)
    assert hints.min_ndim == 2
    assert hints.max_ndim == 3
    assert hints.expected_axes == ["Y", "X"]
    assert hints.squeeze_singleton is True
    assert any("Squeeze singleton" in instr for instr in hints.preprocessing_instructions)


def test_generate_dimension_hints_unknown_returns_none():
    """Unknown functions return None."""
    adapter = SkimageAdapter()
    hints = adapter.generate_dimension_hints("skimage.filters", "non_existent_function")
    assert hints is None


def test_discover_populates_hints():
    """Discovery should populate hints in metadata."""
    adapter = SkimageAdapter()
    config = {"modules": ["skimage.filters"], "include": ["gaussian"]}
    results = adapter.discover(config)

    assert len(results) > 0
    gaussian_meta = next(m for m in results if m.name == "gaussian")
    assert gaussian_meta.hints is not None
    # Skimage gaussian first param is 'image'
    assert "image" in gaussian_meta.hints.inputs
    dim_req = gaussian_meta.hints.inputs["image"].dimension_requirements
    assert dim_req.max_ndim == 3
