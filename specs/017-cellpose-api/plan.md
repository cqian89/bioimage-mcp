# Implementation Plan: Cellpose Object-Oriented API & Stateful Execution

**Branch**: `017-cellpose-api` | **Date**: 2026-01-06 | **Spec**: `/specs/017-cellpose-api/spec.md`
**Input**: Feature specification from `/specs/017-cellpose-api/spec.md`

## Summary

Enable stateful Cellpose execution by supporting `ObjectRef` for model persistence and class-based method calling. This approach allows users to load a model once and reuse it across multiple segmentation tasks, significantly reducing overhead and enabling advanced workflows like fine-tuning.

**CRITICAL**: FR-004 requires implementing `ObjectRef` capture in `workflow-record-json` and `session_replay` reconstruction. This is a blocking deliverable for full workflow reproducibility.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic`, `bioio`, `torch`, `cellpose`  
**Storage**: Local filesystem artifact store (pickle for objects) + SQLite index  
**Testing**: `pytest` (contract, unit, and integration)  
**Target Platform**: Linux-first (GPU support via CUDA)
**Project Type**: Python service + Tool Pack  
**Performance Goals**: Minimize GPU memory churn by reusing model instances; keep MCP messages lean with `ObjectRef`.  
**Constraints**: No large binary payloads in MCP; artifact references only; isolated tool environments.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Stable MCP surface**: No new MCP tools required; `ObjectRef` uses existing `run` and `describe`.
- [x] **Summary-first responses**: `ObjectRef` schema and class-based functions fetched via `describe`.
- [x] **Tool execution isolated**: Cellpose model persistence remains within the `bioimage-mcp-cellpose` subprocess cache.
- [x] **Artifact references only**: Models are passed as `ObjectRef` (URI + metadata), never as raw bytes in MCP.
- [x] **Reproducibility**: `init_params` and `ObjectRef` identifiers are captured in workflow records to allow full session replay.
- [x] **Safety + debuggability**: Eviction of models is managed via runtime policy and/or tool-pack functions (via `run`), NOT new MCP tools; `ObjectRef` validity is checked at runtime with structured errors.

(Reference: `.specify/memory/constitution.md`)

## Implementation Requirements

### Structured Error Model
All `ObjectRef` failures (e.g., expired references, invalid class context) MUST use the project's structured error model:
- **Code**: Specific machine-readable error code.
- **Message**: Human-readable explanation.
- **Details**: Must include `path` and `hint` for resolution.

### Worker IPC Mapping (FR-006, FR-010)
The worker IPC layer (`src/bioimage_mcp/runtimes/worker_ipc.py`) represents stateful initialization through a new `ExecuteRequest.class_context` field:
- **`ClassContext` Model**: A new Pydantic model carrying `python_class` (fully qualified name) and `init_params` (constructor arguments).
- **Parameter Split**: `init_params` are carried in the `ClassContext` for instantiation, while standard `params` remain in the top-level `ExecuteRequest` for method invocation.
- This mapping ensures the worker can correctly instantiate or retrieve the target class instance before execution.

### Testing Additions
- **Kwargs Filtering**: Verify that class method calls correctly filter parameters based on signature.
- **Discovery**: Ensure `describe` correctly separates `ObjectRef` ports from standard IO.
- **Lifecycle**: Test export and `session_replay` to verify object reconstruction from workflow records.

## Project Structure

### Documentation (this feature)

```text
specs/017-cellpose-api/
├── plan.md              # This file
├── research.md          # Research findings and design decisions
├── data-model.md        # ObjectRef and ClassSource definitions
├── quickstart.md        # Example usage scenarios
├── contracts/           # OpenAPI-style schemas
│   ├── object-ref.yaml
│   └── class-source.yaml
└── tasks.md             # Implementation tasks
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── artifacts/
│   └── models.py        # Add ObjectRef type
├── registry/
│   ├── manifest_schema.py # Add target_class to DynamicSource
│   └── dynamic/
│       └── adapters/
│           └── cellpose.py # Update to handle class instantiation
└── runtimes/
    └── worker_ipc.py    # Add class_context to ExecuteRequest

tools/cellpose/
└── bioimage_mcp_cellpose/
    └── entrypoint.py    # Implement object caching and class calling

tests/
├── contract/
│   └── test_object_ref.py # Verify ObjectRef schema
├── integration/
│   └── test_cellpose_stateful.py # E2E stateful segmentation
└── unit/
    └── registry/
        └── test_class_discovery.py # Test class-based introspection
```

**Structure Decision**: Single project layout with updates to core artifact models, registry schemas, and the specific Cellpose tool pack entrypoint.
