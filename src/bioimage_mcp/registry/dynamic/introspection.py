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

        # Extract return type
        returns = self._extract_return_type(func)

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
            returns=returns,
            io_pattern=pattern,
        )

    def _extract_description(self, func: Callable) -> str:
        """Extract description from function docstring."""
        if not func.__doc__:
            return ""

        # Get first line of docstring as description
        lines = func.__doc__.strip().split("\n")
        return lines[0].strip() if lines else ""

    def _extract_return_type(self, func: Callable) -> str | None:
        """Extract return type annotation from function."""
        try:
            sig = inspect.signature(func)
            if sig.return_annotation is not inspect.Signature.empty:
                # Convert annotation to string representation
                return str(sig.return_annotation)
        except (ValueError, TypeError):
            pass
        return None

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
            # Check if parameter has a default value
            has_default = param.default is not inspect.Parameter.empty
            default_value = self._make_json_serializable(param.default) if has_default else None

            # Map Python type annotation to JSON Schema type
            param_type = self._map_type_to_json_schema(
                param.annotation, param.default if has_default else None
            )

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

    def _make_json_serializable(self, value: Any) -> Any:
        """Convert non-JSON-serializable objects to serializable equivalents.

        Args:
            value: Any Python object from parameter default values

        Returns:
            A JSON-serializable representation of the value
        """
        # Return value as-is if it's a basic JSON type (check first for performance)
        if value is None or isinstance(value, (bool, int, float, str)):
            return value

        # Handle range objects (common in scientific functions)
        if isinstance(value, range):
            return list(value)

        # Handle numpy arrays and similar - must be an instance, not a type
        # and the tolist method must be callable without arguments
        if hasattr(value, "tolist") and not isinstance(value, type):
            try:
                return value.tolist()
            except TypeError:
                # Unbound method or other issues - fall through to string conversion
                pass

        # Handle sets
        if isinstance(value, (set, frozenset)):
            return list(value)

        # Handle bytes
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return f"<bytes: {len(value)} bytes>"

        # Handle nested structures
        if isinstance(value, dict):
            return {k: self._make_json_serializable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._make_json_serializable(item) for item in value]

        # For other complex objects, convert to string representation
        try:
            return str(value)
        except Exception:
            return f"<{type(value).__name__}>"

    def _map_type_to_json_schema(self, annotation: Any, default_value: Any = None) -> str:
        """Map Python type annotation to JSON Schema type string.

        If annotation is missing or unknown, uses default_value type if provided.
        """
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

        # Fallback to type of default value if annotation is unhelpful
        if default_value is not None:
            if isinstance(default_value, bool):
                return "boolean"
            if isinstance(default_value, int):
                return "integer"
            if isinstance(default_value, float):
                return "number"

        # Default to string for unknown/complex types
        return "string"
