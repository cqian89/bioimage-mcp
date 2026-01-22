"""
Structured error helpers and exception types for the BioImage-MCP API.
Provides consistent error responses across all MCP tools.
"""

from __future__ import annotations

from bioimage_mcp.api.schemas import ErrorDetail, StructuredError

# Error Codes
VALIDATION_FAILED = "VALIDATION_FAILED"  # Request validation error
NOT_FOUND = "NOT_FOUND"  # Catalog node or artifact not found
ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"  # Specific artifact missing from store or cache
INPUT_MISSING = "INPUT_MISSING"  # External input missing for replay
EXECUTION_FAILED = "EXECUTION_FAILED"  # Tool execution error
PERMISSION_DENIED = "PERMISSION_DENIED"  # Filesystem access denied
SCHEMA_MISMATCH = "SCHEMA_MISMATCH"  # Workflow record schema incompatibility
VERSION_MISMATCH = "VERSION_MISMATCH"  # Tool version differs from recorded
ENVIRONMENT_MISSING = "ENVIRONMENT_MISSING"  # Required tool environment not installed


def validation_error(
    message: str,
    path: str,
    expected: str | None = None,
    actual: str | None = None,
    hint: str = "",
) -> StructuredError:
    """Create a VALIDATION_FAILED error with a single detail.

    Args:
        message: Human-readable error summary
        path: JSON Pointer to the problematic field (e.g., "/inputs/image")
        expected: What was expected
        actual: What was provided
        hint: Actionable guidance for fixing the error

    Returns:
        StructuredError with code VALIDATION_FAILED
    """
    detail = ErrorDetail(path=path, expected=expected, actual=actual, hint=hint)
    return StructuredError(
        code=VALIDATION_FAILED,
        message=message,
        details=[detail],
    )


def version_mismatch_warning(
    message: str,
    fn_id: str,
    recorded_hash: str,
    current_hash: str,
    hint: str = "Results may differ from original run",
) -> StructuredError:
    """Create a VERSION_MISMATCH warning for provenance differences."""
    detail = ErrorDetail(
        path="/steps/*/provenance/lock_hash",
        expected=recorded_hash,
        actual=current_hash,
        hint=hint,
    )
    return StructuredError(
        code=VERSION_MISMATCH,
        message=message,
        details=[detail],
    )


def environment_missing_error(
    message: str,
    env_name: str,
    fn_id: str,
    hint: str = "",
) -> StructuredError:
    """Create an ENVIRONMENT_MISSING error with install suggestion."""
    detail = ErrorDetail(
        path="/steps/*/id",
        expected=f"installed environment: {env_name}",
        actual="not installed",
        hint=hint or f"Run 'bioimage-mcp install {env_name}' to install this environment",
    )
    return StructuredError(
        code=ENVIRONMENT_MISSING,
        message=message,
        details=[detail],
    )


def multi_validation_error(
    message: str,
    details: list[ErrorDetail],
) -> StructuredError:
    """Create a VALIDATION_FAILED error with multiple details.

    Args:
        message: Human-readable summary
        details: List of ErrorDetail objects

    Returns:
        StructuredError with code VALIDATION_FAILED
    """
    return StructuredError(
        code=VALIDATION_FAILED,
        message=message,
        details=details,
    )


def not_found_error(
    message: str,
    path: str,
    expected: str | None = None,
    hint: str = "",
) -> StructuredError:
    """Create a NOT_FOUND error.

    Args:
        message: Human-readable error summary (e.g., "Function 'foo.bar' not found")
        path: JSON Pointer to the field that referenced the missing item
        expected: Description of what was expected to exist
        hint: Actionable guidance (e.g., "Use 'search' to find valid function IDs")

    Returns:
        StructuredError with code NOT_FOUND
    """
    detail = ErrorDetail(path=path, expected=expected, hint=hint)
    return StructuredError(
        code=NOT_FOUND,
        message=message,
        details=[detail],
    )


def artifact_not_found_error(
    message: str,
    path: str,
    expected: str | None = None,
    hint: str = "",
) -> StructuredError:
    """Create an ARTIFACT_NOT_FOUND error.

    Args:
        message: Human-readable error summary (e.g., "ObjectRef not found in cache")
        path: JSON Pointer to the field that referenced the missing artifact
        expected: Description of what was expected
        hint: Actionable guidance (e.g., "Object may have been evicted")

    Returns:
        StructuredError with code ARTIFACT_NOT_FOUND
    """
    detail = ErrorDetail(path=path, expected=expected, hint=hint)
    return StructuredError(
        code=ARTIFACT_NOT_FOUND,
        message=message,
        details=[detail],
    )


def execution_error(
    message: str,
    path: str | None = None,
    hint: str = "",
    details: list[ErrorDetail] | None = None,
) -> StructuredError:
    """Create an EXECUTION_FAILED error.

    Args:
        message: Human-readable error summary
        path: Optional JSON Pointer if error relates to a specific field
        hint: Actionable guidance
        details: Optional list of multiple error details

    Returns:
        StructuredError with code EXECUTION_FAILED
    """
    if details is None:
        details = [ErrorDetail(path=path or "", hint=hint)]

    return StructuredError(
        code=EXECUTION_FAILED,
        message=message,
        details=details,
    )


def permission_denied_error(
    message: str,
    path: str,
    hint: str = "Check filesystem.allowed_read/allowed_write configuration",
) -> StructuredError:
    """Create a PERMISSION_DENIED error.

    Args:
        message: Human-readable error summary
        path: The path that was denied access
        hint: Actionable guidance

    Returns:
        StructuredError with code PERMISSION_DENIED
    """
    detail = ErrorDetail(path=path, hint=hint)
    return StructuredError(
        code=PERMISSION_DENIED,
        message=message,
        details=[detail],
    )


def schema_mismatch_error(
    message: str,
    expected: str,
    actual: str,
    hint: str = "",
) -> StructuredError:
    """Create a SCHEMA_MISMATCH error for workflow records.

    Args:
        message: Human-readable error summary
        expected: Expected schema version or format
        actual: Actual schema version or format found
        hint: Actionable guidance

    Returns:
        StructuredError with code SCHEMA_MISMATCH
    """
    detail = ErrorDetail(path="", expected=expected, actual=actual, hint=hint)
    return StructuredError(
        code=SCHEMA_MISMATCH,
        message=message,
        details=[detail],
    )


def input_missing_error(
    message: str,
    missing_inputs: list[str],
) -> StructuredError:
    """Create an INPUT_MISSING error for missing replay inputs.

    Args:
        message: Human-readable summary
        missing_inputs: List of missing input keys (ref_ids)

    Returns:
        StructuredError with code INPUT_MISSING
    """
    details = [
        ErrorDetail(
            path=f"/inputs/{key}",
            expected="artifact reference",
            actual="missing",
            hint=f"Provide a valid artifact ID for '{key}' in the inputs dictionary",
        )
        for key in missing_inputs
    ]
    return StructuredError(
        code=INPUT_MISSING,
        message=message,
        details=details,
    )


def format_error_summary(error: StructuredError) -> str:
    """Format a StructuredError into human-readable text."""
    lines = [f"Error [{error.code}]: {error.message}"]
    for detail in error.details:
        prefix = f"  - {detail.path}: " if detail.path else "  - "
        if detail.expected and detail.actual:
            lines.append(f"{prefix}Expected {detail.expected}, but got {detail.actual}")
        elif detail.expected:
            lines.append(f"{prefix}Missing {detail.expected}")

        if detail.hint:
            lines.append(f"    Hint: {detail.hint}")

    return "\n".join(lines)
