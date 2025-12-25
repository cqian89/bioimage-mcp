"""
Unit tests for dynamic registry data models.

Tests the IOPattern enum, ParameterSchema, and FunctionMetadata models
used for dynamic function introspection.
"""

import pytest
from bioimage_mcp.registry.dynamic.models import (
    IOPattern,
    ParameterSchema,
    FunctionMetadata,
)


class TestIOPattern:
    """Test cases for IOPattern enum."""

    def test_io_pattern_has_required_values(self):
        """IOPattern enum should have all expected I/O patterns."""
        assert IOPattern.IMAGE_TO_IMAGE == "image_to_image"
        assert IOPattern.IMAGE_TO_LABELS == "image_to_labels"
        assert IOPattern.LABELS_TO_TABLE == "labels_to_table"
        assert IOPattern.SIGNAL_TO_PHASOR == "signal_to_phasor"
        assert IOPattern.PHASOR_TRANSFORM == "phasor_transform"
        assert IOPattern.PHASOR_TO_OTHER == "phasor_to_other"
        assert IOPattern.ARRAY_TO_ARRAY == "array_to_array"
        assert IOPattern.ARRAY_TO_SCALAR == "array_to_scalar"
        assert IOPattern.FILE_TO_SIGNAL == "file_to_signal"
        assert IOPattern.GENERIC == "generic"

    def test_io_pattern_is_string_enum(self):
        """IOPattern values should be strings."""
        pattern = IOPattern.IMAGE_TO_IMAGE
        assert isinstance(pattern, str)
        assert isinstance(pattern.value, str)


class TestParameterSchema:
    """Test cases for ParameterSchema model."""

    def test_parameter_schema_minimal(self):
        """ParameterSchema should work with minimal required fields."""
        param = ParameterSchema(name="sigma", type="number")
        assert param.name == "sigma"
        assert param.type == "number"
        assert param.description == ""
        assert param.default is None
        assert param.required is True
        assert param.enum is None

    def test_parameter_schema_full(self):
        """ParameterSchema should support all optional fields."""
        param = ParameterSchema(
            name="mode",
            type="string",
            description="Edge handling mode",
            default="reflect",
            required=False,
            enum=["reflect", "constant", "wrap"],
        )
        assert param.name == "mode"
        assert param.type == "string"
        assert param.description == "Edge handling mode"
        assert param.default == "reflect"
        assert param.required is False
        assert param.enum == ["reflect", "constant", "wrap"]

    def test_parameter_schema_validates_type(self):
        """ParameterSchema should validate field types."""
        with pytest.raises(Exception):  # Pydantic validation error
            ParameterSchema(name="bad", type=123)  # type must be string


class TestFunctionMetadata:
    """Test cases for FunctionMetadata model."""

    def test_function_metadata_minimal(self):
        """FunctionMetadata should work with minimal required fields."""
        metadata = FunctionMetadata(
            name="gaussian",
            module="skimage.filters",
            qualified_name="skimage.filters.gaussian",
            fn_id="skimage.filters.gaussian",
            source_adapter="scikit-image",
        )
        assert metadata.name == "gaussian"
        assert metadata.module == "skimage.filters"
        assert metadata.qualified_name == "skimage.filters.gaussian"
        assert metadata.fn_id == "skimage.filters.gaussian"
        assert metadata.source_adapter == "scikit-image"
        assert metadata.description == ""
        assert metadata.parameters == {}
        assert metadata.io_pattern == IOPattern.GENERIC
        assert metadata.tags == []

    def test_function_metadata_full(self):
        """FunctionMetadata should support all fields."""
        param = ParameterSchema(name="sigma", type="number", description="Blur radius")
        metadata = FunctionMetadata(
            name="gaussian",
            module="skimage.filters",
            qualified_name="skimage.filters.gaussian",
            fn_id="skimage.filters.gaussian",
            description="Apply Gaussian blur filter",
            parameters={"sigma": param},
            io_pattern=IOPattern.IMAGE_TO_IMAGE,
            source_adapter="scikit-image",
            tags=["filter", "blur", "gaussian"],
        )
        assert metadata.name == "gaussian"
        assert metadata.description == "Apply Gaussian blur filter"
        assert "sigma" in metadata.parameters
        assert metadata.parameters["sigma"].name == "sigma"
        assert metadata.io_pattern == IOPattern.IMAGE_TO_IMAGE
        assert metadata.tags == ["filter", "blur", "gaussian"]

    def test_function_metadata_validates_io_pattern(self):
        """FunctionMetadata should accept valid IOPattern."""
        metadata = FunctionMetadata(
            name="segment",
            module="cellpose.models",
            qualified_name="cellpose.models.segment",
            fn_id="cellpose.segment",
            source_adapter="cellpose",
            io_pattern=IOPattern.IMAGE_TO_LABELS,
        )
        assert metadata.io_pattern == IOPattern.IMAGE_TO_LABELS

    def test_function_metadata_serialization(self):
        """FunctionMetadata should serialize to dict."""
        metadata = FunctionMetadata(
            name="gaussian",
            module="skimage.filters",
            qualified_name="skimage.filters.gaussian",
            fn_id="skimage.filters.gaussian",
            source_adapter="scikit-image",
            io_pattern=IOPattern.IMAGE_TO_IMAGE,
        )
        data = metadata.model_dump()
        assert data["name"] == "gaussian"
        assert data["io_pattern"] == "image_to_image"
