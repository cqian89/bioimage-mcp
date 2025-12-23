# MCP Client Compatibility Guide: Implementation Patterns & Considerations

## Executive Summary
As the Model Context Protocol (MCP) ecosystem matures, server implementers must navigate a fragmented landscape of client behaviors. While the protocol defines standard handshakes and capabilities, implementation support for dynamic features and tool limits varies significantly across major clients like Claude Desktop, Cursor, and Windsurf. 

The "Golden Rule" of MCP development is **Graceful Degradation**: Always assume the client supports only the absolute minimum set of features required for basic operation, and use capability negotiation to unlock advanced functionality. This guide details these differences and provides actionable patterns for robust server development.

---

## Section 1: Client Capability Detection
The primary mechanism for ensuring compatibility is the `initialize` request. During this handshake, the client sends an `initialize` message containing a `capabilities` object. Servers **MUST** inspect this object to understand what the client can do.

### Key Client Capabilities to Watch:
*   **`roots`**: If present, the client can provide the server with a list of filesystem roots. 
    *   *Sub-capability*: `listChanged` (boolean). If `true`, the client can notify the server when these roots change.
*   **`sampling`**: Indicates the client allows the server to request completions from the LLM (useful for "agentic" servers).
*   **`elicitation`**: Support for the server to ask the user for additional information via forms or URLs.
*   **`experimental`**: A placeholder for non-standard features.

### Implementation Pattern: Capability-Aware Logic
Instead of hard-coding features, servers should use a registry or a set of flags derived from the initialization:

```python
# Example logic in a Python server
class MyServer:
    def __init__(self):
        self.can_sample = False
        self.can_watch_roots = False

    async def on_initialize(self, params: InitializeParams):
        client_caps = params.capabilities
        self.can_sample = "sampling" in client_caps
        self.can_watch_roots = client_caps.get("roots", {}).get("listChanged", False)
        
        # Return server capabilities
        return InitializeResult(
            capabilities=ServerCapabilities(
                tools=ToolCapabilities(listChanged=True),
                logging={}
            )
        )
```

**Recommendation**: Never assume a capability is present. If your server *requires* a capability (like `sampling`) that the client lacks, provide a clear, human-readable error message during the initialization phase or when the specific feature is invoked.

---

## Section 2: Dynamic Discovery & Notifications
The `notifications/tools/list_changed` notification allows servers to inform clients that their toolset has changed without requiring a server restart. However, support for this varies.

### Support Matrix:
| Client | `list_changed` Support | Behavior |
| :--- | :--- | :--- |
| **Claude Desktop** | Partial | Often requires an app restart or a manual "Restart MCP Servers" command to refresh the UI reliably. |
| **Windsurf** | High | Natively handles dynamic toolsets; allows toggling tools on/off at runtime. |
| **Cursor** | Limited | Users often report needing to click a "Refresh" icon or reconnect the server to see new tools. |
| **Claude Code** | Full | Highly reactive; designed for CLI-first, dynamic environments. |

### Reliability Pattern: The "Stable Core"
For clients with limited dynamic support, servers should:
1.  Expose a "stable core" of tools that are always available.
2.  Avoid generating tools dynamically based on transient state (e.g., the current file open in the editor) unless you can confirm `listChanged` support in the `initialize` params.
3.  Provide a manual `refresh_tools` tool if your server's toolset is highly dynamic, instructing the user to call it if they don't see expected changes.

---

## Section 3: Navigating Client Tool Limits
A critical discovery for server implementers is that major clients impose hard or soft limits on the total number of tools they can manage. This is often to prevent "context bloat," where the tool schemas consume too much of the LLM's system prompt.

### Key Limits:
*   **Windsurf (Cascade)**: Hard limit of **100 total tools** across all active MCP servers. Users are provided with a UI to manually toggle tools off to stay under this limit.
*   **Cursor**: Historical issues and community reports indicate a **40-tool limit** for some users/versions. Exceeding this often results in tools being truncated or ignored silently.
*   **Claude Desktop**: No documented "hard" limit, but performance (and cost) degrades as the toolset grows because every tool schema is injected into the LLM's context.

### Mitigation Strategy: Tool Modularization
If your project requires more than 40-50 tools, do not put them all in one server.
1.  **Themed Servers**: Split functionality into distinct servers (e.g., `bioimage-mcp-cellpose`, `bioimage-mcp-base`). This allows users to load only the "tool packs" they need.
2.  **Summary Discovery**: Use the `list_tools` endpoint to provide high-level summaries. While the protocol supports pagination, few clients currently implement it.
3.  **Namespace Discipline**: Prefix tools (e.g., `cellpose_segment`) to avoid collisions in clients that merge toolsets from multiple servers.

---

## Section 4: Recommended Fallback Patterns

### Pattern A: Schema Discipline
Keep tool descriptions and parameter schemas concise. 
*   **Bad**: 2-paragraph descriptions for every parameter.
*   **Good**: One-sentence functional descriptions. Use `describe_tool` for complex documentation if the client supports it, but keep the base `list_tools` payload small.

### Pattern B: Path Normalization
Clients like Claude Desktop (especially on Windows) often have restrictive environments.
*   **Symptom**: `npx` or `python` not found even though it's in the user's PATH.
*   **Fix**: Always provide full absolute paths to executables in your installation instructions, or use a "doctor" command to verify the environment from the server's perspective.

### Pattern C: Static Toolsets by Default
Unless the client explicitly advertises `listChanged` in its `initialize` response, assume the toolset is **immutable** for the duration of the session.

---

## Section 5: Verification & Testing
Server implementers should verify compatibility across multiple environments.

### The Testing Matrix:
1.  **MCP Inspector**: The baseline. If it doesn't work here, it won't work anywhere.
2.  **Claude Desktop**: The "standard" chat-style client. Good for testing UI prompts and basic execution.
3.  **Windsurf/Cursor**: The "IDE-style" clients. Crucial for testing tool limits, file-based context (`roots`), and dynamic behavior.
4.  **Claude Code**: The "agent-style" client. Best for testing `sampling` and high-frequency tool calls.

### Diagnostic Tools:
Implement a `doctor` command in your CLI (e.g., `python -m my_mcp_server doctor`). This should check:
- Python/Node version.
- Permissions for key directories.
- Presence of required tool environments (e.g., Conda/Micromamba).
- Connection to any remote APIs.

---

## References
1. [Official MCP Specification - Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle/)
2. [Windsurf Cascade MCP Documentation](https://docs.codeium.com/windsurf/cascade/mcp)
3. [MCP Inspector Guide](https://modelcontextprotocol.io/docs/tools/inspector)
4. [Community Discussion: Cursor Tool Limits](https://github.com/getcursor/cursor/issues/3369)
