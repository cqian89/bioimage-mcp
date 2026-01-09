import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


@pytest.mark.anyio
async def test_mcp_client_start_creates_session():
    """Test that start() creates and initializes a ClientSession."""

    client = TestMCPClient()

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = False

    read_stream = MagicMock(name="read_stream")
    write_stream = MagicMock(name="write_stream")

    @asynccontextmanager
    async def fake_stdio_client(server, errlog):
        assert server.command == "python"
        assert server.args == ["-m", "bioimage_mcp", "serve", "--stdio"]
        assert errlog is client._stderr_file
        yield read_stream, write_stream

    with (
        patch("tests.smoke.utils.mcp_client.stdio_client", fake_stdio_client),
        patch("tests.smoke.utils.mcp_client.ClientSession", return_value=mock_session) as mock_cls,
    ):
        await client.start()

    assert client.session == mock_session
    mock_cls.assert_called_once_with(read_stream, write_stream)
    mock_session.initialize.assert_called_once()


@pytest.mark.anyio
async def test_mcp_client_start_with_timeout_raises_on_timeout():
    """Test timeout behavior for start_with_timeout()."""

    client = TestMCPClient()

    async def slow_start():
        await asyncio.sleep(0.5)

    with patch.object(client, "start", side_effect=slow_start):
        with pytest.raises(asyncio.TimeoutError):
            await client.start_with_timeout(timeout=0.1)


@pytest.mark.anyio
async def test_mcp_client_stop_cleans_up():
    """Test that stop() closes resources and clears session."""

    client = TestMCPClient()
    client.session = MagicMock()
    client._exit_stack = AsyncMock(spec=AsyncExitStack)

    await client.stop()

    client._exit_stack.aclose.assert_called_once()
    assert client.session is None


@pytest.mark.anyio
async def test_mcp_client_cleanup_on_exception():
    """Test cleanup happens on exception."""

    client = TestMCPClient()
    client._exit_stack = AsyncMock(spec=AsyncExitStack)

    try:
        raise ValueError("Oops")
    except ValueError:
        await client.stop()

    client._exit_stack.aclose.assert_called_once()


@pytest.mark.anyio
async def test_mcp_client_call_tool_returns_result():
    """Test call_tool returns result dict."""

    client = TestMCPClient(call_timeout_s=None)
    client.session = AsyncMock()

    mock_content = MagicMock()
    mock_content.text = '{"success": true}'
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    client.session.call_tool.return_value = mock_result

    result = await client.call_tool("test_tool", {"arg1": "val1"})

    assert result == {"success": True}
    client.session.call_tool.assert_called_once_with("test_tool", arguments={"arg1": "val1"})


@pytest.mark.anyio
async def test_mcp_client_call_tool_checked_raises_on_error():
    """Test call_tool_checked raises SmokeTestError on tool failure."""

    client = TestMCPClient(call_timeout_s=None)
    client.session = AsyncMock()

    failed_result = MagicMock()
    failed_result.isError = True
    failed_result.content = "Error details"
    client.session.call_tool.return_value = failed_result

    with pytest.raises(SmokeTestError, match="Tool 'test_tool' failed"):
        await client.call_tool_checked("test_tool", {"arg1": "val1"})
