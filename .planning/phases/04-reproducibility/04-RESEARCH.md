# Phase 4: Reproducibility - Research

**Researched:** 2026-01-22
**Domain:** Session recording, workflow export/replay, and validation.
**Confidence:** HIGH

## Summary

Phase 4 focuses on ensuring analysis sessions are fully recordable and reproducible. Most of the recording infrastructure (REPR-01) is complete, utilizing `SessionStore` and `SessionStep` models to track tool inputs, outputs, and provenance. The export/replay functionality (REPR-02) is ~80% complete but requires refinement in validation, resume capabilities, and interactive feedback.

The research confirms that the existing SQLite-based session storage is sufficient for implementing resume/checkpoint patterns. Parameter validation should leverage `jsonschema` for compatibility with tool manifests. Progress reporting should continue using the polling pattern established in the "8-Tool" surface redesign, as it is transport-agnostic and already supported by the `status` tool.

**Primary recommendation:** Implement replay resume by tracking the `WorkflowRecord` reference in session metadata and using the `session_steps` table as a checkpoint log.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jsonschema` | 4.26.0 | Parameter validation | Used by MCP and supports dynamic schemas from manifests. |
| `pydantic` | 2.x | Data modeling | Core server's standard for API and internal models. |
| `sqlite3` | Standard | Persistence | Already used for tool registry and session tracking. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `bioio` | Latest | Image I/O | Standard for artifact metadata extraction and I/O. |

**Installation:**
```bash
# Core dependencies already installed in bioimage-mcp-base
pip install jsonschema pydantic
```

## Architecture Patterns

### Recommended Project Structure
```
src/bioimage_mcp/
├── api/
│   ├── sessions.py     # SessionService: Export/Replay logic
│   ├── execution.py    # ExecutionService: Low-level run management
│   └── interactive.py  # High-level tool calling & interactive feedback
└── sessions/
    ├── manager.py      # Session lifecycle
    ├── models.py       # DB models (Session, SessionStep)
    └── store.py        # SQLite persistence layer
```

### Pattern 1: Checkpointing via DB (Resume)
**What:** Use the `session_steps` table to track progress of a multi-step replay.
**When to use:** During `session_replay`, check for existing canonical steps in the session to skip already-executed operations.
**Example:**
```python
# During replay initialization
existing_steps = store.list_step_attempts(session_id)
last_success_idx = max((s.ordinal for s in existing_steps if s.status == "success"), default=-1)
# Start replay from last_success_idx + 1
```

### Pattern 2: Dynamic Parameter Validation
**What:** Validate `params_overrides` against the `params_schema` provided in the tool's descriptor.
**When to use:** Before starting a replay or a new run.
**Example:**
```python
from jsonschema import validate, ValidationError
# Source: Official jsonschema docs
try:
    validate(instance=params, schema=fn_descriptor.params_schema)
except ValidationError as e:
    # Map to StructuredError
    pass
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Validation | Custom logic | `jsonschema` | Handles complex types, ranges, and nested structures correctly. |
| Progress Bars | Custom events | `status` tool | Polling is transport-agnostic and fits the MCP client-server model. |
| Time Tracking | Manual `time.time()` | `datetime(UTC)` | Avoids timezone issues and satisfies reproducibility requirements. |

## Common Pitfalls

### Pitfall 1: Version Drift
**What goes wrong:** Replaying a workflow on a newer version of a tool pack might yield different results.
**Why it happens:** Tool logic changes even if the interface remains the same.
**How to avoid:** Store `lock_hash` (checksum of manifest) in provenance and warn users on mismatch (as decided in CONTEXT.md).

### Pitfall 2: Memory Artifact Eviction
**What goes wrong:** Dependent steps fail because an `ObjectRef` produced in an earlier step was evicted from memory.
**Why it happens:** Restarting the server or exceeding memory limits.
**How to avoid:** Use the `reconstruct_object` pattern already implemented in `ExecutionService` to re-run the constructor step if needed.

## Code Examples

### Structured Error for Missing Input
```python
# Pattern for prompting users for missing inputs
from bioimage_mcp.api.errors import validation_error

error = validation_error(
    message="Missing external input: 'image_path'",
    path="/inputs/image_path",
    expected="ArtifactRef (BioImageRef)",
    hint="This workflow requires an external image. Please provide a path or artifact ID."
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-run replay | Multi-step session replay | Jan 2026 | Allows reproducing complex multi-tool workflows. |
| Manual I/O tracking | Provenance with lock_hash | Jan 2026 | Ensures version-locked reproducibility. |

## Open Questions

1. **Structured Error Report Schema:** What is the exact schema for "Resume state persistence mechanism"?
   - *Finding:* We can use the existing `session_steps` table, but we might need an `is_replay` flag or a `parent_session_id` in the `sessions` table to group replay attempts.
   - *Recommendation:* Keep it simple—use the `session_id` provided by the client as the key for resume.

2. **Dry-run Output Format:**
   - *Finding:* Currently returns empty outputs.
   - *Recommendation:* Return "virtual" artifact references (e.g., `dry-run-step0-output1`) to allow the client to see the expected workflow graph.

## Sources

### Primary (HIGH confidence)
- `src/bioimage_mcp/api/sessions.py` - Current replay implementation.
- `src/bioimage_mcp/api/schemas.py` - Standard API models.
- `src/bioimage_mcp/api/errors.py` - Structured error helpers.
- `Context7: /websites/mcp-use_python` - MCP progress reporting patterns.

### Secondary (MEDIUM confidence)
- `jsonschema` official documentation for dynamic validation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Already integrated into the core server.
- Architecture: HIGH - Follows established SQLite/Pydantic patterns in the repo.
- Pitfalls: HIGH - Based on known issues in bioimage analysis (version drift, memory artifacts).

**Research date:** 2026-01-22
**Valid until:** 2026-02-22
