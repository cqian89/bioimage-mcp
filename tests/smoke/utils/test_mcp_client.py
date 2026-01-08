import asyncio
import subprocess
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports are expected to fail until the implementation is created
from tests.smoke.utils.mcp_client import SmokeTestError, TestMCPClient


def test_smoke_test_error_is_exception():
    """Test SmokeTestError is an Exception subclass."""
    assert issubclass(SmokeTestError, Exception)


def test_smoke_test_error_message():
    """Test SmokeTestError stores error message."""
    msg = "Test error message"
    error = SmokeTestError(msg)
    assert str(error) == msg


def test_mcp_client_init():
    """Test TestMCPClient initializes with None session."""
    client = TestMCPClient()
    assert client.session is None
    assert isinstance(client._exit_stack, AsyncExitStack)


@pytest.mark.asyncio
async def test_mcp_client_start_creates_session():
    """Test that start() creates a session (async)."""
    client = TestMCPClient()

    # Mock the internal MCP client components
    mock_session = AsyncMock()

    # Mock process and its streams
    mock_process = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    mock_process.stderr.readline = AsyncMock(return_value=b"")
    mock_process.stdin = MagicMock()
    mock_process.stdin.drain = AsyncMock()

    with (
        patch(
            "tests.smoke.utils.mcp_client.asyncio.create_subprocess_exec",
            return_value=mock_process,
        ) as mock_exec,
        patch(
            "tests.smoke.utils.mcp_client.ClientSession", return_value=mock_session
        ) as mock_session_cls,
    ):
        await client.start()

        assert client.session == mock_session
        assert mock_exec.called
        assert mock_session_cls.called
        # Verify initialize was called on the session
        mock_session.initialize.assert_called_once()

        # Check command line arguments
        args, kwargs = mock_exec.call_args
        assert args == ("python", "-m", "bioimage_mcp", "serve", "--stdio")
        assert kwargs["stdin"] == subprocess.PIPE
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE


@pytest.mark.asyncio
async def test_mcp_client_start_with_timeout_raises_on_timeout():
    """Test timeout behavior (mock the server start to be slow)."""
    client = TestMCPClient()

    async def slow_exec(*args, **kwargs):
        await asyncio.sleep(0.5)
        mock_process = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        return mock_process

    with patch(
        "tests.smoke.utils.mcp_client.asyncio.create_subprocess_exec",
        side_effect=slow_exec,
    ):
        with pytest.raises(asyncio.TimeoutError):
            await client.start_with_timeout(timeout=0.1)


@pytest.mark.asyncio
async def test_mcp_client_stop_cleans_up():
    """Test that stop() closes resources."""
    client = TestMCPClient()
    client._exit_stack = AsyncMock(spec=AsyncExitStack)

    # Mock process for cleanup
    mock_process = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.wait = AsyncMock()
    client._process = mock_process

    await client.stop()

    client._exit_stack.aclose.assert_called_once()
    mock_process.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_client_cleanup_on_exception():
    """Test cleanup happens on exception."""
    client = TestMCPClient()
    client._exit_stack = AsyncMock(spec=AsyncExitStack)

    try:
        # Simulate some work that fails
        raise ValueError("Oops")
    except ValueError:
        await client.stop()

    client._exit_stack.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_client_call_tool_returns_result():
    """Test call_tool returns result dict."""
    client = TestMCPClient()
    client.session = AsyncMock()

    # Mock a tool result that has content
    mock_content = MagicMock()
    mock_content.text = '{"success": true}'
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    client.session.call_tool.return_value = mock_result

    result = await client.call_tool("test_tool", {"arg1": "val1"})

    assert result == {"success": True}
    client.session.call_tool.assert_called_once_with("test_tool", arguments={"arg1": "val1"})


@pytest.mark.asyncio
async def test_mcp_client_call_tool_checked_raises_on_error():
    """Test call_tool_checked raises SmokeTestError on tool failure."""
    client = TestMCPClient()
    client.session = AsyncMock()

    # Mock a failed tool result
    failed_result = MagicMock()
    failed_result.isError = True
    failed_result.content = "Error details"
    client.session.call_tool.return_value = failed_result

    with pytest.raises(SmokeTestError, match="Tool 'test_tool' failed"):
        await client.call_tool_checked("test_tool", {"arg1": "val1"})
