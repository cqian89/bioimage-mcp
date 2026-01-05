# Research: MCP Interface Redesign

**Feature**: 016-mcp-interface-redesign  
**Date**: 2026-01-05  
**Status**: Complete

## Overview

This document records research decisions for the MCP Interface Redesign. The proposal document (`docs/plan/Proposal_MCP_Interface_Redesign.md`) already contains extensive findings from live server interaction, so this research focuses on consolidating decisions and capturing any remaining technical choices.

---

## Decision 1: Tool Surface Reduction (13 → 8 tools)

### Decision
Reduce the MCP tool surface from 13 tools to exactly 8 tools with consistent naming.

### Rationale
- Current surface mixes concepts (catalog browsing, introspection, execution, artifacts, sessions) with inconsistent naming
- LLMs benefit from minimal, consistent interfaces
- Aligns with Constitution Section I (Stable MCP Surface)

### Alternatives Considered
1. **Keep all tools, fix naming**: Rejected - doesn't reduce complexity, maintains redundancy
2. **Minimal 5-tool surface**: Rejected - loses important functionality (artifact_info, session replay)
3. **Backwards-compatible wrapper layer**: Rejected - proposal explicitly deprioritizes backward compatibility

### Implementation Impact
- Remove: `describe_tool`, `activate_functions`, `deactivate_functions`, `run_workflow`, `resume_session`, `export_artifact`
- Rename/consolidate: remaining 8 tools per proposal mapping

---

## Decision 1b: Remove export_artifact Tool

### Decision
Remove `export_artifact` from the MCP surface. Artifacts are file-backed and accessible via their URI returned by `artifact_info`.

### Rationale
- Keeps the 8-tool surface clean and focused on core operations
- Artifacts already have file:// URIs that clients can access directly
- `artifact_info` returns the URI, size, checksums - sufficient for client-side retrieval
- Removes complexity of server-side path allowlist management for exports

### Alternatives Considered
1. **Keep as 9th tool**: Rejected - adds surface complexity, clients can access files directly
2. **Expose via MCP Resources**: Deferred - may add later for direct client byte streaming

### Implementation Impact
- Remove `export_artifact` handler from `api/artifacts.py`
- Clients access artifacts via URI from `artifact_info` response

---

## Decision 2: Child Counts for Navigation

### Decision
All `list` responses MUST include `children.total` and `children.by_type` for non-leaf nodes, replacing boolean `has_children`.

### Rationale
- LLMs need quantitative information to decide navigation strategy
- A module with 5 functions should be expanded; one with 500 should use search
- Reduces unnecessary API calls for catalog exploration

### Alternatives Considered
1. **Lazy child loading with preview**: Rejected - requires multiple round-trips
2. **Flat list with filtering**: Rejected - loses hierarchical structure benefits
3. **Keep has_children boolean**: Rejected - insufficient for LLM navigation decisions

### Implementation Impact
- Modify `ListResponse` schema to include `ChildCounts` model
- Update catalog traversal to compute counts during listing

---

## Decision 3: Artifact Ports vs Params Separation

### Decision
Function descriptions MUST return `inputs`, `outputs`, and `params_schema` as separate fields. Artifact ports MUST NOT appear inside `params_schema`.

### Rationale
- Current schema sometimes duplicates artifact ports in params (e.g., `image` in both)
- LLMs need clear distinction: artifacts are references, params are JSON values
- Prevents validation confusion and improves call construction

### Alternatives Considered
1. **Mark artifact params with type annotation**: Rejected - still pollutes params_schema
2. **Flatten all to params**: Rejected - loses semantic distinction critical for execution

### Implementation Impact
- Refactor schema generation in manifest processing
- Ensure artifact input/output ports are extracted before params_schema construction

---

## Decision 4: Structured Error Model

### Decision
All tools MUST return errors with shape: `{code, message, details: [{path, expected, actual, hint}]}`.

### Rationale
- Machine-parseable errors enable LLM self-correction
- JSON Pointer paths precisely identify problematic fields
- Hints provide actionable guidance without full documentation lookup

### Alternatives Considered
1. **Simple error strings**: Rejected - not machine-parseable
2. **Error codes only**: Rejected - lacks context for correction
3. **Full error documentation links**: Rejected - adds latency, requires external lookup

### Implementation Impact
- Define `StructuredError`, `ErrorDetail` Pydantic models
- Update all handlers to raise/return structured errors
- Add contract tests for error shapes

---

## Decision 5: Session Export with External Input Tracking

### Decision
Workflow records MUST distinguish `external_inputs` (caller-provided) from step-derived artifacts using `source` field with values `"external"` or `"step"`.

### Rationale
- Enables replay on different starting data (the primary use case)
- Clear provenance for reproducibility audits
- Matches proposal's workflow record format

### Alternatives Considered
1. **Track all artifacts equally**: Rejected - cannot identify rebindable inputs
2. **User-annotated input markers**: Rejected - error-prone, adds complexity to caller
3. **Infer from missing prior steps**: Rejected - fragile with complex workflows

### Implementation Impact
- Session state must track artifact provenance during execution
- Export logic must classify inputs as external vs step-derived
- Replay logic must use `source` field for rebinding

---

## Decision 6: Dry-Run Validation Parity

### Decision
`dry_run=true` MUST perform identical validation to real execution. Missing required inputs must fail under dry-run the same as in real execution.

### Rationale
- Current behavior accepts incomplete dry-runs, misleading LLMs
- Dry-run should be a reliable pre-flight check
- Enables LLMs to validate before committing to expensive operations

### Alternatives Considered
1. **Relaxed dry-run for exploration**: Rejected - creates false confidence
2. **Separate validation endpoint**: Rejected - adds complexity to tool surface

### Implementation Impact
- Share validation logic between dry-run and real execution paths
- Return `status: "validation_failed"` with structured errors

---

## Decision 7: Session Replay with Overrides

### Decision
`session_replay` supports `params_overrides` (by function id) and `step_overrides` (by step index).

### Rationale
- Users often want to tweak parameters when replaying
- Step-level overrides allow targeted adjustments
- Function-level overrides apply to all occurrences of a function

### Alternatives Considered
1. **No overrides - clone and edit**: Rejected - loses workflow record integrity
2. **Only step-level overrides**: Rejected - inconvenient when same function appears multiple times
3. **Interactive parameter prompting**: Rejected - not suitable for automated replay

### Implementation Impact
- Replay execution must check for overrides before applying recorded params
- Override validation must match function's params_schema

---

## Decision 8: Tool Naming Conventions

### Decision
Use short, verb-based names: `list`, `describe`, `search`, `run`, `status`, `artifact_info`, `session_export`, `session_replay`.

### Rationale
- Consistent with proposal and updated Constitution
- Short names reduce prompt overhead
- Verb-first convention clearly indicates action

### Alternatives Considered
1. **Noun-based (e.g., `tools`, `artifacts`)**: Rejected - less action-oriented
2. **Namespaced (e.g., `catalog.list`, `session.export`)**: Rejected - MCP tools are already namespaced at server level
3. **Underscore style (e.g., `list_catalog`)**: Rejected - longer, inconsistent with target

### Implementation Impact
- Tool registration in FastMCP uses new names
- All documentation and tests updated

---

## Technology Choices

### FastMCP for Tool Registration
**Chosen**: Continue using `FastMCP` SDK for MCP server implementation.  
**Rationale**: Already in use, well-suited for Python async patterns.  
**Alternatives**: Raw MCP SDK - more boilerplate, less convenient.

### Pydantic v2 for Schemas
**Chosen**: Pydantic v2 for all request/response models.  
**Rationale**: Already used throughout codebase; provides JSON Schema generation.  
**Alternatives**: dataclasses + manual validation - less integrated.

### pytest for Contract Tests
**Chosen**: pytest with contract test pattern.  
**Rationale**: Matches existing test structure; contract tests verify API stability.  
**Alternatives**: None considered - pytest is standard.

---

## Open Questions (None)

All significant decisions are resolved by the proposal document. Implementation can proceed.

---

## References

- [Proposal_MCP_Interface_Redesign.md](../../docs/plan/Proposal_MCP_Interface_Redesign.md) - Primary source
- [Constitution](../../.specify/memory/constitution.md) - Section I (Stable MCP Surface) updated to match
- [Feature Spec](./spec.md) - Functional requirements extracted from proposal
