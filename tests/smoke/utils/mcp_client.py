import asyncio
import json
import subprocess
from contextlib import AsyncExitStack

import anyio
import mcp.types as types
from mcp import ClientSession
from mcp.shared.message import SessionMessage


class SmokeTestError(Exception):
    """Exception raised for smoke test failures with diagnostic context."""

    pass


class TestMCPClient:
    """Wrapper for MCP client with lifecycle management."""

    __test__ = False

    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self._stderr_buffer: list[str] = []
        self._process: asyncio.subprocess.Process | None = None
        self._tasks: list[asyncio.Task] = []

    def get_stderr(self) -> str:
        """Return captured stderr."""
        return "\n".join(self._stderr_buffer)

    async def _read_stderr(self):
        """Task to read stderr from the subprocess."""
        if not self._process or not self._process.stderr:
            return

        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                if line_str:
                    self._stderr_buffer.append(line_str)
        except (asyncio.CancelledError, Exception):
            pass

    async def start(self):
        """Start server subprocess and initialize session.

        Uses: python -m bioimage_mcp serve --stdio
        """
        # Start the process with all streams piped for capture.
        # We use asyncio.create_subprocess_exec directly to have access to the stderr pipe.
        self._process = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "bioimage_mcp",
            "serve",
            "--stdio",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Set up memory streams for MCP ClientSession.
        # ClientSession expects JSONRPCMessage wrapped in SessionMessage on the read stream.
        # We use buffered streams (capacity 100) to avoid deadlocks during the
        # initialization handshake.
        read_stream_writer, read_stream = anyio.create_memory_object_stream(100)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(100)

        # Ensure streams are closed when exit stack is closed.
        self._exit_stack.push_async_callback(read_stream.aclose)
        self._exit_stack.push_async_callback(write_stream.aclose)
        self._exit_stack.push_async_callback(read_stream_writer.aclose)
        self._exit_stack.push_async_callback(write_stream_reader.aclose)

        # Task to read stdout and feed read_stream
        async def stdout_reader():
            if not self._process or not self._process.stdout:
                return
            try:
                async with read_stream_writer:
                    while True:
                        line = await self._process.stdout.readline()
                        if not line:
                            break
                        line_str = line.decode().strip()
                        if not line_str:
                            continue
                        try:
                            message = types.JSONRPCMessage.model_validate_json(line_str)
                            await read_stream_writer.send(SessionMessage(message))
                        except Exception as e:
                            # Forward exception to session for error handling if parsing fails.
                            # The MCP ClientSession will handle these as transport errors.
                            await read_stream_writer.send(e)
            except (asyncio.CancelledError, anyio.ClosedResourceError):
                pass

        # Task to read write_stream and feed stdin
        async def stdin_writer():
            if not self._process or not self._process.stdin:
                return
            try:
                async with write_stream_reader:
                    async for session_message in write_stream_reader:
                        json_str = session_message.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        self._process.stdin.write((json_str + "\n").encode())
                        await self._process.stdin.drain()
            except (
                asyncio.CancelledError,
                anyio.ClosedResourceError,
                ConnectionResetError,
            ):
                pass

        # Start background tasks
        self._tasks.append(asyncio.create_task(self._read_stderr()))
        self._tasks.append(asyncio.create_task(stdout_reader()))
        self._tasks.append(asyncio.create_task(stdin_writer()))

        # Initialize session
        self.session = ClientSession(read_stream, write_stream)
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
        # 1. Close session and streams via exit stack
        await self._exit_stack.aclose()
        self.session = None

        # 2. Cancel background tasks
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # 3. Terminate process
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except (TimeoutError, ProcessLookupError, Exception):
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

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
