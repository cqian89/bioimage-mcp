"""
Function introspection for dynamic registry.

Analyzes Python functions to generate FunctionMetadata and ParameterSchema
automatically using inspect.signature.
"""

import inspect
from collections.abc import Callable
from typing import Any

from bioimage_mcp.registry.dynamic.models import (
    FunctionMetadata,
    IOPattern,
    ParameterSchema,
)


class Introspector:
    """Introspects Python functions to generate metadata."""

    def introspect(
        self,
        func: Callable,
        source_adapter: str,
        io_pattern: IOPattern | None = None,
    ) -> FunctionMetadata:
        """
        Analyze a function and generate its metadata.

        Args:
            func: The function to introspect
            source_adapter: Identifier for the source adapter
            io_pattern: Optional I/O pattern override (defaults to GENERIC)

        Returns:
            Complete function metadata with parameters
        """
        # Extract function identity
        name = func.__name__
        module = func.__module__.split(".")[-1]  # Last component only
        qualified_name = f"{module}.{name}"
        fn_id = qualified_name

        # Extract description from docstring
        description = self._extract_description(func)

        # Extract parameters
        parameters = self._extract_parameters(func)

        # Use provided io_pattern or default to GENERIC
        pattern = io_pattern if io_pattern is not None else IOPattern.GENERIC

        return FunctionMetadata(
            name=name,
            module=module,
            qualified_name=qualified_name,
            fn_id=fn_id,
            source_adapter=source_adapter,
            description=description,
            parameters=parameters,
            io_pattern=pattern,
        )

    def _extract_description(self, func: Callable) -> str:
        """Extract description from function docstring."""
        if not func.__doc__:
            return ""

        # Get first line of docstring as description
        lines = func.__doc__.strip().split("\n")
        return lines[0].strip() if lines else ""

    def _parse_docstring_params(self, func: Callable) -> dict[str, str]:
        """Extract parameter descriptions from NumPy-style docstring.

        Args:
            func: Function to parse docstring from

        Returns:
            Dict mapping parameter name to its description
        """
        if not func.__doc__:
            return {}

        try:
            from numpydoc.docscrape import FunctionDoc

            doc = FunctionDoc(func)
            descriptions = {}
            for param in doc["Parameters"]:
                # Parameter name may include type like "image : ndarray"
                name = param.name.split(":")[0].strip()
                # Description is a list of strings, join them
                desc = " ".join(param.desc).strip()
                if desc:
                    descriptions[name] = desc
            return descriptions
        except ImportError:
            # numpydoc not available - graceful degradation
            return {}
        except Exception:
            # Any parsing error - graceful degradation
            return {}

    def _extract_parameters(self, func: Callable) -> dict[str, ParameterSchema]:
        """Extract parameter schemas from function signature."""
        sig = inspect.signature(func)
        parameters = {}

        # Parse docstring for parameter descriptions
        param_descriptions = self._parse_docstring_params(func)

        for param_name, param in sig.parameters.items():
            # Map Python type annotation to JSON Schema type
            param_type = self._map_type_to_json_schema(param.annotation)

            # Check if parameter has a default value
            has_default = param.default is not inspect.Parameter.empty
            default_value = param.default if has_default else None

            # Parameter is required if it has no default
            is_required = not has_default

            # Get description from docstring if available
            description = param_descriptions.get(param_name, "")

            parameters[param_name] = ParameterSchema(
                name=param_name,
                type=param_type,
                description=description,
                default=default_value,
                required=is_required,
            )

        return parameters

    def _map_type_to_json_schema(self, annotation: Any) -> str:
        """Map Python type annotation to JSON Schema type string."""
        # Handle common built-in types
        if annotation is int or annotation == "int":
            return "integer"
        elif annotation is str or annotation == "str":
            return "string"
        elif annotation is float or annotation == "float":
            return "number"
        elif annotation is bool or annotation == "bool":
            return "boolean"

        # Handle string annotations (forward references)
        if isinstance(annotation, str):
            if "int" in annotation.lower():
                return "integer"
            elif "str" in annotation.lower():
                return "string"
            elif "float" in annotation.lower():
                return "number"
            elif "bool" in annotation.lower():
                return "boolean"

        # Default to string for unknown/complex types
        return "string"
