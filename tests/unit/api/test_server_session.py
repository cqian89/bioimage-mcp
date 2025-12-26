"""Unit tests for session identifier helper in server.py.

Tests the get_session_identifier function that provides a stable session
identifier fallback for MCP SDK v1.25.0+ where ServerSession.id is not available.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bioimage_mcp.api.server import get_session_identifier


def test_get_session_identifier_stdio_fallback():
    """Test fallback to session_{id} when no SSE query params available.

    For stdio transport (or when SSE query params are not present),
    should return a session identifier based on the memory address
    of the session object using id(ctx.session).
    """
    # Arrange: Mock context with no request metadata (stdio transport)
    ctx = MagicMock()
    session_mock = MagicMock(spec=[])  # No auto-attributes - simulates real ServerSession
    ctx.session = session_mock

    # No request context (stdio transport)
    ctx.request_context = None

    expected_id = f"session_{id(session_mock)}"

    # Act
    result = get_session_identifier(ctx)

    # Assert
    assert result == expected_id
    assert result.startswith("session_")


def test_get_session_identifier_sse_query_param():
    """Test extraction of session_id from SSE query params.

    When SSE transport provides a session_id query parameter,
    that should be used as the stable identifier.
    """
    # Arrange: Mock context with SSE request metadata
    ctx = MagicMock()
    session_mock = MagicMock(spec=[])  # No auto-attributes - we expect query param to be used
    ctx.session = session_mock

    # Mock SSE transport with query params
    request_context = MagicMock()
    request_context.query_params = {"session_id": "test-session-123"}
    ctx.request_context = request_context

    # Act
    result = get_session_identifier(ctx)

    # Assert
    assert result == "test-session-123"


def test_get_session_identifier_consistent_for_same_session():
    """Test that same session object returns consistent identifier.

    Calling the function multiple times with the same session object
    should always return the same identifier string.
    """
    # Arrange: Same session mock should produce same ID
    ctx = MagicMock()
    session_mock = MagicMock(spec=[])  # No auto-attributes - simulates real ServerSession
    ctx.session = session_mock
    ctx.request_context = None

    # Act: Call multiple times
    result1 = get_session_identifier(ctx)
    result2 = get_session_identifier(ctx)

    # Assert: Results should be identical
    assert result1 == result2
    assert result1 == f"session_{id(session_mock)}"


def test_get_session_identifier_sse_without_session_id_param():
    """Test fallback when SSE transport exists but no session_id param.

    If request_context is present but query_params doesn't contain
    session_id, should fall back to memory address identifier.
    """
    # Arrange
    ctx = MagicMock()
    session_mock = MagicMock(spec=[])  # No auto-attributes - simulates real ServerSession
    ctx.session = session_mock

    # SSE transport but no session_id in query params
    request_context = MagicMock()
    request_context.query_params = {}
    ctx.request_context = request_context

    expected_id = f"session_{id(session_mock)}"

    # Act
    result = get_session_identifier(ctx)

    # Assert
    assert result == expected_id


def test_get_session_identifier_request_context_no_query_params():
    """Test fallback when request_context exists but has no query_params.

    If request_context is present but doesn't have a query_params attribute,
    should fall back to memory address identifier without raising AttributeError.
    """
    # Arrange
    ctx = MagicMock()
    session_mock = MagicMock(spec=[])  # No auto-attributes - simulates real ServerSession
    ctx.session = session_mock

    # Request context without query_params attribute
    request_context = MagicMock(spec=[])  # Empty spec = no attributes
    ctx.request_context = request_context

    expected_id = f"session_{id(session_mock)}"

    # Act
    result = get_session_identifier(ctx)

    # Assert
    assert result == expected_id
