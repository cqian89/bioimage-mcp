import asyncio
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class SmokeTestError(Exception):
    """Exception raised for smoke test failures with diagnostic context."""

    pass


class TestMCPClient:
    """Wrapper for MCP client with lifecycle management."""

    __test__ = False

    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def start(self):
        """Start server subprocess and initialize session.

        Uses: python -m bioimage_mcp serve --stdio
        """
        params = StdioServerParameters(
            command="python",
            args=["-m", "bioimage_mcp", "serve", "--stdio"],
            env=None,  # inherit environment
        )

        # In actual mcp SDK, stdio_client(params) returns an async context manager.
        # But in tests, it might be mocked as an async function.
        cm_or_coro = stdio_client(params)
        if asyncio.iscoroutine(cm_or_coro) or hasattr(cm_or_coro, "__await__"):
            cm = await cm_or_coro
        else:
            cm = cm_or_coro

        streams = await self._exit_stack.enter_async_context(cm)

        # Handle the case where streams is not a tuple (e.g. in tests)
        if isinstance(streams, (list, tuple)) and len(streams) == 2:
            read, write = streams
        else:
            read, write = streams, streams

        self.session = ClientSession(read, write)
        await self._exit_stack.enter_async_context(self.session)
        await self.session.initialize()

    async def start_with_timeout(self, timeout: float = 30.0):
        """Start server with timeout for initialization.

        Raises asyncio.TimeoutError if server fails to start within timeout.
        """
        async with asyncio.timeout(timeout):
            await self.start()

    async def stop(self):
        """Clean shutdown of session and subprocess."""
        await self._exit_stack.aclose()
        self.session = None

    async def call_tool(self, tool: str, arguments: dict) -> dict:
        """Call MCP tool and return result.

        Raises RuntimeError if session not started.
        """
        if self.session is None:
            raise RuntimeError("Session not started. Call start() first.")
        result = await self.session.call_tool(tool, arguments=arguments)

        # Parse result content
        if hasattr(result, "content") and result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, "text"):
                try:
                    return json.loads(content.text)
                except (json.JSONDecodeError, TypeError):
                    return {"text": content.text}

        # Fallback for when the result is already a dict (e.g. in tests)
        if isinstance(result, dict):
            return result

        return {}

    async def call_tool_checked(self, tool: str, arguments: dict) -> dict:
        """Call MCP tool and raise SmokeTestError on failure."""
        if self.session is None:
            raise RuntimeError("Session not started. Call start() first.")
        result = await self.session.call_tool(tool, arguments=arguments)

        # Check for error
        is_error = False
        if hasattr(result, "isError"):
            is_error = result.isError
        elif isinstance(result, dict) and result.get("isError"):
            is_error = True

        if is_error:
            error_msg = "Unknown error"
            if hasattr(result, "content"):
                error_msg = str(result.content)
            elif isinstance(result, dict) and "content" in result:
                error_msg = str(result["content"])
            raise SmokeTestError(f"Tool '{tool}' failed: {error_msg}")

        # Parse result
        if hasattr(result, "content") and result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, "text"):
                try:
                    return json.loads(content.text)
                except (json.JSONDecodeError, TypeError):
                    return {"text": content.text}

        if isinstance(result, dict):
            return result

        return {}
