# bioimage-mcp

Bioimage-MCP is an MCP server for bioimage analysis. It keeps a stable, compact
LLM-facing interface while orchestrating a customizable set of analysis tools in
isolated conda environments (e.g., Cellpose, StarDist, PhasorPy, Fiji).

Key ideas:
- Stable discovery-first MCP API (paginated `list/search/describe`; avoids context bloat)
- File-backed artifact references for I/O (OME-Zarr preferred; OME-TIFF supported)
- Per-tool environment isolation and subprocess execution
- Workflow recording and replay for reproducibility

Project docs:
- `initial_planning/Bioimage-MCP_PRD.md`
- `initial_planning/Bioimage-MCP_ARCHITECTURE.md`
- `.specify/memory/constitution.md`
