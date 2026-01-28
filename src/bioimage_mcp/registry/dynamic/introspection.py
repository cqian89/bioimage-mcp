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

    def _normalize_description(self, description: str) -> str:
        """Normalize whitespace in descriptions to single spaces."""
        return " ".join(description.split()).strip()

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

    def _parse_docstring_params(self, func: Callable) -> dict[str, dict[str, str]]:
        """Extract parameter info from NumPy-style docstring.

        Returns:
            Dict mapping parameter name to {"description": str, "type": str}
        """
        if not func.__doc__:
            return {}

        param_info = {}

        # Try docstring-parser first (unified support for Numpydoc, Google, Sphinx)
        try:
            import docstring_parser

            doc = docstring_parser.parse(func.__doc__)
            for param in doc.params:
                description = self._normalize_description(param.description or "")
                param_info[param.arg_name] = {
                    "description": description,
                    "type": param.type_name or "",
                }
            if param_info:
                return param_info
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback to numpydoc for NumPy-specific high-fidelity
        try:
            from numpydoc.docscrape import FunctionDoc

            doc = FunctionDoc(func)
            for param in doc["Parameters"]:
                # Parameter name may include type like "image : ndarray"
                name = param.name.split(":")[0].strip()
                # Description is a list of strings, join them
                desc = self._normalize_description(" ".join(param.desc))
                # param.type contains the type annotation from docstring
                doc_type = param.type if hasattr(param, "type") and param.type else ""
                param_info[name] = {"description": desc, "type": doc_type}
            return param_info
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

        # Parse docstring for parameter info (description and type hint)
        param_info = self._parse_docstring_params(func)

        for param_name, param in sig.parameters.items():
            # Skip variadic parameters (*args, **kwargs) as they are not
            # easily represented in a flat MCP parameter schema and
            # can cause issues if provided as named parameters (T054)
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            # Check if parameter has a default value
            has_default = param.default is not inspect.Parameter.empty
            default_value = self._make_json_serializable(param.default) if has_default else None

            # Map Python type annotation to JSON Schema type
            # Priority: 1) Signature annotation, 2) Default value type (if conclusive), 3) Docstring type
            annotation = param.annotation

            # If signature annotation is empty, try to infer from default value first
            if annotation is inspect.Parameter.empty or annotation is Any:
                if has_default and isinstance(param.default, (bool, int, float, str)):
                    # Default value provides strong type signal - use it directly
                    if isinstance(param.default, bool):
                        annotation = bool
                    elif isinstance(param.default, int):
                        annotation = int
                    elif isinstance(param.default, float):
                        annotation = float
                    elif isinstance(param.default, str):
                        annotation = str
                elif param_name in param_info:
                    # Fall back to docstring type only if no strong default signal
                    doc_type = param_info[param_name].get("type")
                    if doc_type:
                        annotation = doc_type

            param_type = self._map_type_to_json_schema(
                annotation, param.default if has_default else None
            )

            # Parameter is required if it has no default
            is_required = not has_default

            # Get description from docstring if available
            info = param_info.get(param_name, {})
            description = info.get("description", "")

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
        elif annotation in (list, tuple) or annotation in ("list", "tuple"):
            return "array"

        # Handle string annotations (forward references)
        if isinstance(annotation, str):
            lower_annotation = annotation.lower()
            if "int" in lower_annotation and "point" not in lower_annotation:
                return "integer"
            # Check for list/tuple BEFORE str (since "list of str" contains both)
            elif "list" in lower_annotation or "tuple" in lower_annotation:
                return "array"
            elif "str" in lower_annotation:
                return "string"
            elif "float" in lower_annotation:
                return "number"
            elif "bool" in lower_annotation:
                return "boolean"
            # Scientific array types - treat as number for scalar compatibility
            elif "arraylike" in lower_annotation or "array_like" in lower_annotation:
                # ArrayLike often means "scalar or array" - use number for MCP
                return "number"
            elif "ndarray" in lower_annotation:
                # numpy ndarray - for scalar params, treat as number
                return "number"

        # Handle typing module types like Optional[float], Union[int, float]
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            # Get type arguments (e.g., (int, None) for Optional[int])
            args = getattr(annotation, "__args__", ())
            # Filter out None type
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                # Recursively map the first non-None type
                return self._map_type_to_json_schema(non_none_args[0], default_value)

        # Fallback to type of default value if annotation is unhelpful
        if default_value is not None:
            if isinstance(default_value, bool):
                return "boolean"
            if isinstance(default_value, int):
                return "integer"
            if isinstance(default_value, float):
                return "number"

            # Handle list/tuple default values
            if isinstance(default_value, (list, tuple)):
                return "array"

        # Default to string for unknown/complex types
        return "string"
