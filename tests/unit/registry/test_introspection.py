"""
Unit tests for function introspection.

Tests the Introspector class that analyzes Python functions to generate
FunctionMetadata and ParameterSchema automatically.
"""

from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import (
    FunctionMetadata,
    IOPattern,
    ParameterSchema,
)


# Sample functions for introspection testing
def simple_add(a: int, b: int = 0) -> int:
    """Add two integers."""
    return a + b


def image_filter(
    image: "numpy.ndarray", sigma: float = 1.0, mode: str = "reflect"
) -> "numpy.ndarray":
    """Apply a filter to an image.

    Args:
        image: Input image array
        sigma: Filter radius
        mode: Edge handling mode

    Returns:
        Filtered image array
    """
    return image


def gaussian_filter_numpy_style(
    image: "numpy.ndarray", sigma: float = 1.0, truncate: float = 4.0
) -> "numpy.ndarray":
    """Apply a Gaussian filter to smooth an image.

    Parameters
    ----------
    image : numpy.ndarray
        Input image array to be filtered. Can be 2D or 3D.
    sigma : float, optional
        Standard deviation for Gaussian kernel. Higher values produce
        more blurring. Default is 1.0.
    truncate : float, optional
        Truncate the filter at this many standard deviations.
        Default is 4.0.

    Returns
    -------
    numpy.ndarray
        Filtered image with same shape as input.
    """
    return image


def func_with_array_param(
    data: "ndarray",
    properties: tuple = ("label", "bbox"),
    columns: list = ["a", "b"],
) -> dict:
    """Function with array-type parameters."""
    return {}


class TestIntrospector:
    """Test cases for Introspector function signature analysis."""

    def test_introspect_simple_function(self):
        """Introspector should extract metadata from a simple function."""
        introspector = Introspector()

        metadata = introspector.introspect(
            simple_add,
            source_adapter="test-adapter",
        )

        assert isinstance(metadata, FunctionMetadata)
        assert metadata.name == "simple_add"
        assert metadata.module == "test_introspection"
        assert metadata.qualified_name == "test_introspection.simple_add"
        assert metadata.source_adapter == "test-adapter"
        assert metadata.description == "Add two integers."

    def test_introspect_function_parameters(self):
        """Introspector should extract parameter schemas with types and defaults."""
        introspector = Introspector()

        metadata = introspector.introspect(
            simple_add,
            source_adapter="test-adapter",
        )

        # Should have 2 parameters
        assert len(metadata.parameters) == 2

        # Check parameter 'a' (required, no default)
        assert "a" in metadata.parameters
        param_a = metadata.parameters["a"]
        assert isinstance(param_a, ParameterSchema)
        assert param_a.name == "a"
        assert param_a.type == "integer"
        assert param_a.default is None
        assert param_a.required is True

        # Check parameter 'b' (optional, has default)
        assert "b" in metadata.parameters
        param_b = metadata.parameters["b"]
        assert isinstance(param_b, ParameterSchema)
        assert param_b.name == "b"
        assert param_b.type == "integer"
        assert param_b.default == 0
        assert param_b.required is False

    def test_introspect_function_with_docstring(self):
        """Introspector should extract description and parameter docs from docstring."""
        introspector = Introspector()

        metadata = introspector.introspect(
            image_filter,
            source_adapter="test-adapter",
        )

        # Should extract description
        assert "filter" in metadata.description.lower()

        # Should have 3 parameters
        assert len(metadata.parameters) == 3

        # Check parameter documentation
        assert "image" in metadata.parameters
        assert "sigma" in metadata.parameters
        assert "mode" in metadata.parameters

        # Sigma should have default value
        param_sigma = metadata.parameters["sigma"]
        assert param_sigma.default == 1.0
        assert param_sigma.type == "number"
        assert param_sigma.required is False

        # Mode should have default value
        param_mode = metadata.parameters["mode"]
        assert param_mode.default == "reflect"
        assert param_mode.type == "string"
        assert param_mode.required is False

    def test_introspect_generates_fn_id(self):
        """Introspector should generate a unique fn_id for the function."""
        introspector = Introspector()

        metadata = introspector.introspect(
            simple_add,
            source_adapter="test-adapter",
        )

        # fn_id should be qualified name
        assert metadata.fn_id == metadata.qualified_name
        assert metadata.fn_id == "test_introspection.simple_add"

    def test_introspect_default_io_pattern(self):
        """Introspector should default to GENERIC io_pattern."""
        introspector = Introspector()

        metadata = introspector.introspect(
            simple_add,
            source_adapter="test-adapter",
        )

        # Should default to GENERIC pattern
        assert metadata.io_pattern == IOPattern.GENERIC

    def test_introspect_with_custom_io_pattern(self):
        """Introspector should accept custom io_pattern override."""
        introspector = Introspector()

        metadata = introspector.introspect(
            image_filter,
            source_adapter="test-adapter",
            io_pattern=IOPattern.IMAGE_TO_IMAGE,
        )

        # Should use provided pattern
        assert metadata.io_pattern == IOPattern.IMAGE_TO_IMAGE

    def test_introspect_numpy_style_docstring(self):
        """Introspector should extract parameter descriptions from NumPy-style docstrings."""
        introspector = Introspector()

        metadata = introspector.introspect(
            gaussian_filter_numpy_style,
            source_adapter="test-adapter",
        )

        # Should extract description (first line/summary)
        assert "Gaussian filter" in metadata.description
        assert "smooth" in metadata.description

        # Should have 3 parameters
        assert len(metadata.parameters) == 3

        # Check parameter 'image' - should have full description from Parameters section
        assert "image" in metadata.parameters
        param_image = metadata.parameters["image"]
        assert param_image.required is True
        # This is the key assertion that will FAIL - should extract multi-line description
        assert "Input image array to be filtered" in param_image.description
        assert "Can be 2D or 3D" in param_image.description

        # Check parameter 'sigma' - should have full description
        assert "sigma" in metadata.parameters
        param_sigma = metadata.parameters["sigma"]
        assert param_sigma.required is False
        assert param_sigma.default == 1.0
        assert param_sigma.type == "number"
        # This should also FAIL - should extract multi-line description
        assert "Standard deviation for Gaussian kernel" in param_sigma.description
        assert "Higher values produce more blurring" in param_sigma.description

        # Check parameter 'truncate' - should have full description
        assert "truncate" in metadata.parameters
        param_truncate = metadata.parameters["truncate"]
        assert param_truncate.required is False
        assert param_truncate.default == 4.0
        assert param_truncate.type == "number"
        # This should also FAIL
        assert "Truncate the filter at this many standard deviations" in param_truncate.description

    def test_introspect_array_default_parameters(self):
        """Introspector should detect array type for list/tuple default values."""
        introspector = Introspector()

        metadata = introspector.introspect(
            func_with_array_param,
            source_adapter="test-adapter",
        )

        # Check properties (tuple default)
        assert "properties" in metadata.parameters
        param_properties = metadata.parameters["properties"]
        assert param_properties.type == "array"
        assert param_properties.default == [
            "label",
            "bbox",
        ]  # _make_json_serializable converts to list

        # Check columns (list default)
        assert "columns" in metadata.parameters
        param_columns = metadata.parameters["columns"]
        assert param_columns.type == "array"
        assert param_columns.default == ["a", "b"]
