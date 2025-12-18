# Comparison: MicroscopyLM vs Bioimage-MCP

| Proposed Bioimage-MCP Feature | Existing MicroscopyLM Feature | Reuse Status | Reuse Strategy |
| :--- | :--- | :--- | :--- |
| **Tool Discovery** (Manifests, Registry) | `miclm.tools.registry` (Layered loading: Builtin/User/Project) | **Full** | Use `load_tool_registry` and `ToolSpec` as the core of the MCP tool discovery. Add `entrypoint` support if missing. |
| **Environment Isolation** (Conda/Lock) | `miclm.env.manager` (Doctor, Bootstrap, Check) | **Full** | Reuse `EnvironmentManager` and `EnvironmentConfig`. Adapt `bootstrap_environment` to use `micromamba` if not already preferred. |
| **Execution Model** (Subprocess Shim) | `miclm.executors.python_subproc` (JSON I/O, `conda run`) | **Full** | Use `PythonSubprocessExecutor` as the backend for `run()` in the MCP server. |
| **CLI** (Install, Doctor, Config) | `miclm.cli` (Typer app, `env`, `tools` subcommands) | **Partial** | Rename `miclm` to `bioimage-mcp`. Adapt `miclm env` -> `bioimage-mcp doctor/install`. Remove session-specific commands (`init`, `add`) if not needed for MCP server mode. |
| **MCP Server** (Stdio/SSE) | *None* | **None** | Implement new `server.py` using `mcp` SDK. Wire it to `miclm.tools` and `miclm.executors`. |
| **Workflow Planning** (Linear Plan) | `miclm.plan` (Linear planning logic exists) | **Partial** | Adapt `miclm plan` logic to be exposed as `create_workflow` MCP tool. Ensure it produces the specified linear plan format. |
| **Artifacts** (OME-Zarr Refs) | `miclm.dataio` (Basic I/O) | **Partial** | Enhance `miclm`'s artifact handling to strictly follow the `BioImageRef`/`ref:` schema. Integrate `ngff-zarr`. |
| **Replay Workflow** | `miclm run` (Executes plans) | **Partial** | Wrap `miclm run` logic into `replay_workflow` MCP tool. |
| **User Config** (`~/.bioimage-mcp`) | `miclm.config` (Loads from `~/.miclm`) | **Full** | Just change the directory name constant to `.bioimage-mcp`. |

## Summary
MicroscopyLM provides a very strong foundation, covering ~70% of the backend logic required for Bioimage-MCP. The main missing piece is the **MCP Server layer** itself, which needs to be built on top of the existing `miclm` components (`tools`, `env`, `executors`).
