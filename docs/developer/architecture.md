# Architecture

## High-Level Design

Bioimage-MCP is designed to be a stable bridge between AI agents and diverse bioimage analysis tools.

### Core Components

1.  **MCP Server**: The entry point for LLMs. Handles discovery (`list_tools`), execution (`call_tool`), and resource management.
2.  **Artifact Store**: A managed directory structure that holds all data. Tools read/write from here.
3.  **Runtime Manager**: Orchestrates subprocess execution of tools in isolated environments.
4.  **Tool Registry**: Discovers available tools from manifests.

### Design Documents

For detailed architectural decisions and history, please refer to the planning documents:

*   [**Architecture Deep Dive**](../plan/Bioimage-MCP_ARCHITECTURE.md)
*   [**Product Requirements Document (PRD)**](../plan/Bioimage-MCP_PRD.md)
*   [**Interactive Tool Calling Proposal**](../plan/Proposal_Interactive_Tool_Calling.md)

### Key Decisions

*   **Subprocess Isolation**: We chose subprocesses over in-process execution to allow tools to have conflicting dependencies (e.g., different Python versions, conflicting library versions).
*   **Artifact-First I/O**: To support large images (GBs or TBs), we never pass image data in API payloads. We pass references.
*   **Standardized bioio Integration**: We use `bioio` as the universal cross-environment image artifact layer, ensuring consistent 5D TCZYX data access without custom wrapper overhead.
