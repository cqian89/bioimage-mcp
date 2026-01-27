"""Unit tests for introspection utilities (T000a, T000b).

These tests verify the introspect_python_api() and introspect_argparse()
utilities that extract JSON Schema from Python function signatures and
argparse parsers respectively.
"""

from __future__ import annotations

import argparse
from typing import Any

from bioimage_mcp.runtimes.introspect import introspect_argparse, introspect_python_api


class TestIntrospectPythonApi:
    """Tests for introspect_python_api() utility (T000a)."""

    def test_extracts_parameter_names(self) -> None:
        """Test that parameter names are extracted from function signature."""

        def sample_func(x: int, name: str = "default") -> None:
            pass

        descriptions: dict[str, str] = {}
        schema = introspect_python_api(sample_func, descriptions)

        assert "properties" in schema
        assert "x" in schema["properties"]
        assert "name" in schema["properties"]

    def test_extracts_type_annotations(self) -> None:
        """Test that type annotations are mapped to JSON Schema types."""

        def sample_func(
            i: int,
            f: float,
            s: str,
            b: bool,
        ) -> None:
            pass

        schema = introspect_python_api(sample_func, {})

        assert schema["properties"]["i"]["type"] == "integer"
        assert schema["properties"]["f"]["type"] == "number"
        assert schema["properties"]["s"]["type"] == "string"
        assert schema["properties"]["b"]["type"] == "boolean"

    def test_extracts_default_values(self) -> None:
        """Test that default values are included in schema."""

        def sample_func(
            threshold: float = 0.5,
            name: str = "default",
            count: int = 10,
        ) -> None:
            pass

        schema = introspect_python_api(sample_func, {})

        assert schema["properties"]["threshold"]["default"] == 0.5
        assert schema["properties"]["name"]["default"] == "default"
        assert schema["properties"]["count"]["default"] == 10

    def test_marks_required_parameters(self) -> None:
        """Test that parameters without defaults are marked as required."""

        def sample_func(required_param: int, optional_param: str = "opt") -> None:
            pass

        schema = introspect_python_api(sample_func, {})

        assert "required_param" in schema["required"]
        assert "optional_param" not in schema["required"]

    def test_uses_curated_descriptions(self) -> None:
        """Test that curated descriptions override fallback."""

        def sample_func(diameter: float = 30.0) -> None:
            pass

        descriptions = {"diameter": "Estimated cell diameter in pixels."}
        schema = introspect_python_api(sample_func, descriptions)

        assert (
            schema["properties"]["diameter"]["description"] == "Estimated cell diameter in pixels."
        )

    def test_fallback_description_for_unknown_params(self) -> None:
        """Test that unknown params get a fallback description."""

        def sample_func(unknown_param: int = 5) -> None:
            pass

        schema = introspect_python_api(sample_func, {})

        # Should have some fallback description, not be empty
        assert "description" in schema["properties"]["unknown_param"]
        assert len(schema["properties"]["unknown_param"]["description"]) > 0

    def test_excludes_self_parameter(self) -> None:
        """Test that 'self' parameter is excluded by default."""

        class Sample:
            def method(self, x: int) -> None:
                pass

        schema = introspect_python_api(Sample.method, {})

        assert "self" not in schema["properties"]
        assert "x" in schema["properties"]

    def test_excludes_specified_parameters(self) -> None:
        """Test that custom exclusion list works."""

        def sample_func(x: int, internal: str = "skip") -> None:
            pass

        schema = introspect_python_api(
            sample_func,
            {},
            exclude_params={"internal"},
        )

        assert "internal" not in schema["properties"]
        assert "x" in schema["properties"]

    def test_skips_var_positional_and_keyword(self) -> None:
        """Test that *args and **kwargs are skipped."""

        def sample_func(x: int, *args: Any, **kwargs: Any) -> None:
            pass

        schema = introspect_python_api(sample_func, {})

        assert "x" in schema["properties"]
        assert "args" not in schema["properties"]
        assert "kwargs" not in schema["properties"]

    def test_parses_docstring_descriptions(self) -> None:
        """Test that descriptions are extracted from docstring."""

        def sample_func(diameter: float = 30.0) -> None:
            """Sample function.

            Args:
                diameter: Estimated cell diameter in pixels.
            """
            pass

        schema = introspect_python_api(sample_func, {})
        assert (
            schema["properties"]["diameter"]["description"] == "Estimated cell diameter in pixels."
        )

    def test_omits_artifact_ports(self) -> None:
        """Test that artifact ports are omitted from schema."""

        def sample_func(image: str, labels: str, threshold: float = 0.5) -> None:
            pass

        schema = introspect_python_api(sample_func, {})
        assert "image" not in schema["properties"]
        assert "labels" not in schema["properties"]
        assert "threshold" in schema["properties"]

    def test_output_is_deterministic(self) -> None:
        """Test that output schema keys are sorted."""

        def sample_func(z: int, a: int, m: int) -> None:
            pass

        schema1 = introspect_python_api(sample_func, {})
        schema2 = introspect_python_api(sample_func, {})

        assert list(schema1["properties"].keys()) == ["a", "m", "z"]
        assert schema1 == schema2


class TestIntrospectArgparse:
    """Tests for introspect_argparse() utility (T000b)."""

    def test_extracts_argument_names(self) -> None:
        """Test that argument dest names are extracted from parser."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--diameter", type=float)
        parser.add_argument("--model", type=str)

        schema = introspect_argparse(parser, {})

        assert "diameter" in schema["properties"]
        assert "model" in schema["properties"]

    def test_extracts_type_from_argparse(self) -> None:
        """Test that argparse type= is mapped to JSON Schema types."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--count", type=int)
        parser.add_argument("--threshold", type=float)
        parser.add_argument("--name", type=str)

        schema = introspect_argparse(parser, {})

        assert schema["properties"]["count"]["type"] == "integer"
        assert schema["properties"]["threshold"]["type"] == "number"
        assert schema["properties"]["name"]["type"] == "string"

    def test_extracts_boolean_flags(self) -> None:
        """Test that store_true/store_false actions become boolean."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--no-cache", action="store_false", dest="cache")

        schema = introspect_argparse(parser, {})

        assert schema["properties"]["verbose"]["type"] == "boolean"
        assert schema["properties"]["verbose"]["default"] is False
        assert schema["properties"]["cache"]["type"] == "boolean"
        assert schema["properties"]["cache"]["default"] is True

    def test_extracts_default_values(self) -> None:
        """Test that default values are included."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--threshold", type=float, default=0.4)

        schema = introspect_argparse(parser, {})

        assert schema["properties"]["threshold"]["default"] == 0.4

    def test_extracts_choices_as_enum(self) -> None:
        """Test that choices become enum in schema."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--model", choices=["cyto", "nuclei", "cyto2"])

        schema = introspect_argparse(parser, {})

        assert schema["properties"]["model"]["enum"] == ["cyto", "nuclei", "cyto2"]

    def test_uses_curated_descriptions(self) -> None:
        """Test that curated descriptions override argparse help."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--diameter", help="Original help text")

        descriptions = {"diameter": "Curated description for diameter."}
        schema = introspect_argparse(parser, descriptions)

        assert (
            schema["properties"]["diameter"]["description"] == "Curated description for diameter."
        )

    def test_uses_argparse_help_as_fallback(self) -> None:
        """Test that argparse help is used when no curated description."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--diameter", help="The cell diameter in pixels")

        schema = introspect_argparse(parser, {})

        assert schema["properties"]["diameter"]["description"] == "The cell diameter in pixels"

    def test_marks_required_arguments(self) -> None:
        """Test that required=True arguments are in required list."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--input", required=True)
        parser.add_argument("--output")

        schema = introspect_argparse(parser, {})

        assert "input" in schema["required"]
        assert "output" not in schema["required"]

    def test_excludes_help_and_version(self) -> None:
        """Test that help and version are excluded by default."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--diameter", type=float)
        # help is added by default

        schema = introspect_argparse(parser, {})

        assert "help" not in schema["properties"]
        assert "diameter" in schema["properties"]

    def test_skips_positional_arguments(self) -> None:
        """Test that positional arguments are skipped."""
        parser = argparse.ArgumentParser()
        parser.add_argument("input_file")  # positional
        parser.add_argument("--threshold", type=float)

        schema = introspect_argparse(parser, {})

        assert "input_file" not in schema["properties"]
        assert "threshold" in schema["properties"]
