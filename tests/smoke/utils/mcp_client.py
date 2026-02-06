import asyncio
import json
import os
import tempfile
import time
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from tests.smoke.utils.interaction_logger import InteractionLogger


class SmokeTestError(Exception):
    """Exception raised for smoke test failures with diagnostic context."""


class TestMCPClient:
    """Wrapper for MCP client with lifecycle management."""

    __test__ = False

    def __init__(
        self,
        logger: InteractionLogger | None = None,
        *,
        call_timeout_s: float | None = 60.0,
        server_env: dict[str, str] | None = None,
    ):
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self._logger = logger
        self._call_timeout_s = call_timeout_s
        self._server_env = server_env if server_env is not None else self._display_env_overrides()
        self._stderr_file = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        self._exit_stack.callback(self._stderr_file.close)

    @staticmethod
    def _display_env_overrides() -> dict[str, str]:
        keys = {
            "DISPLAY",
            "WAYLAND_DISPLAY",
            "XDG_RUNTIME_DIR",
            "WSL_DISTRO_NAME",
            "WSL_INTEROP",
        }
        return {key: value for key in keys if (value := os.environ.get(key))}

    def get_stderr(self) -> str:
        """Return captured server stderr."""

        try:
            self._stderr_file.flush()
            self._stderr_file.seek(0)
            return self._stderr_file.read()
        except Exception:
            return ""

    async def start(self):
        """Start server subprocess and initialize MCP session."""

        server = StdioServerParameters(
            command="python",
            args=["-m", "bioimage_mcp", "serve", "--stdio"],
            env=self._server_env or None,
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server, errlog=self._stderr_file)
        )

        self.session = ClientSession(read_stream, write_stream)
        await self._exit_stack.enter_async_context(self.session)
        await self.session.initialize()

    async def start_with_timeout(self, timeout: float = 30.0):
        """Start server with timeout for initialization.

        Raises:
            asyncio.TimeoutError: If server fails to start within timeout.
        """

        async with asyncio.timeout(timeout):
            await self.start()

    async def stop(self):
        """Clean shutdown of MCP session and server subprocess."""

        await self._exit_stack.aclose()
        self.session = None

    async def call_tool(self, tool: str, arguments: dict) -> dict:
        """Call MCP tool and return parsed JSON result."""

        if self.session is None:
            raise RuntimeError("Session not started. Call start() first.")

        correlation_id = None
        start_time = None
        if self._logger:
            correlation_id = self._logger.log_request(tool, arguments)
            start_time = time.perf_counter()

        try:
            if self._call_timeout_s is None:
                result = await self.session.call_tool(tool, arguments=arguments)
            else:
                async with asyncio.timeout(self._call_timeout_s):
                    result = await self.session.call_tool(tool, arguments=arguments)
        except Exception as e:
            if self._logger and correlation_id is not None and start_time is not None:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._logger.log_response(correlation_id, {"error": str(e)}, duration_ms)
            raise

        parsed: dict = {}
        if hasattr(result, "content") and result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, "text"):
                try:
                    parsed = json.loads(content.text)
                except (json.JSONDecodeError, TypeError):
                    parsed = {"text": content.text}
        elif isinstance(result, dict):
            parsed = result

        if self._logger and correlation_id is not None and start_time is not None:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._logger.log_response(correlation_id, parsed, duration_ms)

        return parsed

    async def call_tool_checked(self, tool: str, arguments: dict) -> dict:
        """Call MCP tool and raise SmokeTestError on tool failure."""

        if self.session is None:
            raise RuntimeError("Session not started. Call start() first.")

        correlation_id = None
        start_time = None
        if self._logger:
            correlation_id = self._logger.log_request(tool, arguments)
            start_time = time.perf_counter()

        try:
            if self._call_timeout_s is None:
                result = await self.session.call_tool(tool, arguments=arguments)
            else:
                async with asyncio.timeout(self._call_timeout_s):
                    result = await self.session.call_tool(tool, arguments=arguments)

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

            parsed: dict = {}
            if hasattr(result, "content") and result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, "text"):
                    try:
                        parsed = json.loads(content.text)
                    except (json.JSONDecodeError, TypeError):
                        parsed = {"text": content.text}
            elif isinstance(result, dict):
                parsed = result

            if self._logger and correlation_id and start_time:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._logger.log_response(correlation_id, parsed, duration_ms)

            return parsed
        except Exception as e:
            if self._logger and correlation_id and start_time:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._logger.log_response(correlation_id, {"error": str(e)}, duration_ms)
            raise
