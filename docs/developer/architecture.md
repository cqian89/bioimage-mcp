# Architecture

## High-Level Design

Bioimage-MCP is designed to be a stable bridge between AI agents and diverse bioimage analysis tools.

### Core Components

1.  **MCP Server**: The entry point for LLMs. Handles discovery (`list_tools`), execution (`call_tool`), and resource management.
2.  **Artifact Store**: A managed directory structure that holds all data. Tools read/write from here. Includes support for both persistent file-backed and ephemeral memory-backed storage.
3.  **Runtime Manager**: Orchestrates subprocess execution of tools in isolated environments. Manages the lifecycle of persistent worker processes.
4.  **Tool Registry**: Discovers available tools from manifests and validates their execution requirements.

### Persistent Workers

> *New in v0.1.1 (Spec 011)*

Tool environments use **persistent worker processes** that remain alive for the duration of an MCP session. This enables:

- **Memory-backed artifacts**: Data can remain in worker memory between tool calls.
- **Session isolation**: Each session has independent workers per environment.
- **Efficient chaining**: Avoids disk I/O overhead for multi-step workflows.

#### Worker Lifecycle

1.  First tool call in an environment lazily starts a worker process.
2.  Subsequent calls reuse the same worker.
3.  Worker crash triggers automatic memory artifact invalidation.
4.  Session end terminates all associated workers.

### Memory Artifacts (`mem://`)

Memory artifacts are references to data residing in worker process memory:

```text
URI format: mem://<session_id>/<env_id>/<ref_id>
Example:    mem://session-abc123/bioimage-mcp-base/img-xyz789
```

**Key Properties**:
- **Ephemeral**: Lost on worker restart or session end.
- **Fast**: No disk serialization overhead.
- **Session-scoped**: Only valid within the creating session.

**Materialization**: Use `base.bioio.export` to convert `mem://` to file-backed artifacts when:
- Data needs to persist beyond the session.
- Data needs to cross environment boundaries.

### Cross-Environment Handoff

When data must move between tool environments (e.g., from base to cellpose):

1.  **Format Negotiation**: Target tool declares required formats.
2.  **Source Materialization**: Source env exports to interchange format (default: OME-TIFF).
3.  **Provenance Recording**: Handoff recorded in workflow provenance.

### Design Documents

For detailed architectural decisions and history, please refer to the planning documents:

*   [**Architecture Deep Dive**](../plan/Bioimage-MCP_ARCHITECTURE.md)
*   [**Product Requirements Document (PRD)**](../plan/Bioimage-MCP_PRD.md)
*   [**Interactive Tool Calling Proposal**](../plan/Proposal_Interactive_Tool_Calling.md)

### Key Decisions

*   **Subprocess Isolation**: We chose subprocesses over in-process execution to allow tools to have conflicting dependencies (e.g., different Python versions, conflicting library versions).
*   **Artifact-First I/O**: To support large images (GBs or TBs), we never pass image data in API payloads. We pass references.
*   **Standardized bioio Integration**: We use `bioio` as the universal cross-environment image artifact layer, ensuring consistent 5D TCZYX data access without custom wrapper overhead.
*   **Persistent Workers**: We use persistent workers instead of transient subprocesses to enable memory-backed artifacts and avoid repeated startup costs for multi-step workflows within the same environment.
*   **Memory Artifacts**: The `mem://` scheme provides a standard way to reference in-memory data while maintaining the artifact-reference-only principle for MCP messages.
