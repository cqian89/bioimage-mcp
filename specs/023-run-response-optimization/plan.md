# Implementation Plan: Run Response Token Optimization

**Branch**: `023-run-response-optimization` | **Date**: Tue Jan 13 2026 | **Spec**: [proposal.md](./proposal.md)
**Input**: Reduce token bloat in MCP `run` tool responses via model cleanup + verbosity control (default `minimal`).

## Summary

This plan implements a verbosity-aware response serializer for the MCP `run` tool to reduce typical success responses by ~90% while preserving full detail on demand.

Key changes:
- **ArtifactRef cleanup (global)**: remove duplicated dimension fields from `ArtifactRef` (keep dims/shape/dtype/pps only in `metadata`), and exclude `None` / empty collections from serialization.
- **`run` response shaping (MCP only)**: add `verbosity` (`minimal` default, `standard`, `full`) and return only what an LLM needs to chain calls.
- **Chaining safety**: ensure minimal/standard outputs (which may omit `uri`) can still be passed back as inputs without breaking execution.

Backward compatibility is explicitly **not** a constraint for this milestone.

## Technical Context

- **Language/Version**: Python 3.13
- **Core stack**: MCP Python SDK, Pydantic v2
- **Execution model**: isolated tool subprocesses; core server inflates artifact refs before dispatch
- **Storage**: file-backed artifact store + SQLite index; memory artifacts tracked in MemoryStore
- **Testing**: `pytest` (unit/contract/integration/smoke), `ruff`

## Constitution Check

1. [x] **Stable MCP Surface / anti-bloat**: this change reduces default `run` payload size; adds an explicit `verbosity` parameter (no new tools).
2. [x] **Summary-first**: `minimal` becomes summary-first for execution responses; full detail remains available.
3. [x] **Isolated tool execution**: unchanged.
4. [x] **Artifacts only**: no binary payloads embedded; responses contain artifact handles and optional summaries.
5. [x] **Reproducibility**: workflow record still generated/stored; just hidden unless `full`.
6. [x] **Safety/observability**: `log_ref` forced on failures regardless of verbosity.

## Key Decisions (resolve proposal ambiguities)

| Area | Decision | Rationale |
|------|----------|-----------|
| Where verbosity applies | Only MCP `run` tool response serialization | Limits ripple; `ExecutionService`/`status` keep rich data for provenance and replay |
| Status values | Keep existing (`success`, `failed`, `validation_failed`) | Avoid broad internal renames; treat `failed` as "error" for log inclusion rules |
| `size_mb` | Include in `minimal` and `standard` (derived from `size_bytes`) | Meets FR-004 and improves LLM readability |
| `uri` in `minimal` | Omit for file-backed artifacts; include for memory-backed (`mem://`, `obj://`) | File paths are large; memory URIs can be required by object workflows |
| `summary` key | Remove from public `run` responses at all verbosity levels | Redundant; `minimal` flattens summary fields |
| Inline log content | Never inline in `run` responses (all verbosities) | Prevents accidental token explosions; use `artifact_info(text_preview_bytes=...)` |
| `channel_names` | Truncate to 10 items in `minimal`/`standard`; full list in `full` | Prevents pathological payload growth |

## Impact Analysis (what else this touches)

### 1) Tool chaining behavior
- **Risk**: today many tests/clients pass the *entire* output dict (including `uri`) back as the next step input.
- **Change**: `minimal` omits `uri` for file artifacts.
- **Mitigation**:
  - Update input normalization to accept *partial* artifact dicts that contain `ref_id` but not `uri`.
  - Update smoke tests to pass `ref_id` strings by default.

### 2) ArtifactInfo and dimension access
- **Risk**: `ArtifactRef.dims`/`ndim` currently exist and are used by `artifact_info`.
- **Change**: remove top-level dimension fields from `ArtifactRef`.
- **Mitigation**: update `src/bioimage_mcp/api/artifacts.py` to read dims/ndim from `ref.metadata`.

### 3) Provenance and workflow records
- **Risk**: some internal tests expect `workflow_record` in status outputs.
- **Change**: hide `workflow_record` only from MCP `run` responses for `minimal`/`standard`.
- **Mitigation**: do not change `ExecutionService` storage behavior; `status()` still exposes full run outputs.

## Target Response Shapes

### `minimal` (default)
Top-level fields:
- `run_id`, `status`, `fn_id`, `outputs`
- `warnings` only if non-empty
- `log_ref` only if `status != "success"`

Per-output artifact object contains only (if available):
- `ref_id`, `type`, `shape`, `dims`, `dtype`, `size_mb`
- optional `physical_pixel_sizes`, `format`, `channel_names`
- plus `uri` only for memory-backed artifacts

### `standard`
- Same top-level behavior as `minimal`
- Artifact output is a trimmed ArtifactRef:
  - include `ref_id`, `type`, `uri`, `format`, `storage_type`, `size_bytes`, `size_mb`, `metadata`
  - exclude `checksums`, `created_at`
  - exclude `metadata.file_metadata` entirely

### `full`
- Includes full ArtifactRef payload (including `checksums`, `created_at`, full `metadata.file_metadata`)
- Includes `log_ref` and `workflow_record` on success

## Project Structure (changes)

### Source Code
```text
src/bioimage_mcp/
├── api/
│   ├── server.py                 # UPDATE: add verbosity param; apply serializer; rename id->fn_id in response
│   ├── execution.py              # UPDATE: inflate partial refs (dict with ref_id but missing uri)
│   └── artifacts.py              # UPDATE: dims/ndim pulled from metadata
├── artifacts/
│   ├── models.py                 # UPDATE: remove top-level ndim/dims/shape/dtype/pps; exclude None/empties
│   └── store.py                  # UPDATE: stop populating removed top-level fields
└── ...

src/bioimage_mcp/api/
└── serializers.py                # NEW: RunResponseSerializer (minimal/standard/full)
```

### Tests
```text
tests/
├── unit/
│   ├── api/test_run_response_serializer.py   # NEW: serializer unit tests
│   └── artifacts/test_artifactref_dump.py    # NEW/UPDATE: model cleanup tests
├── contract/
│   └── test_run_response_verbosity.py        # NEW: contract-level shapes for each verbosity
└── smoke/
    ├── test_smoke_basic.py                   # UPDATE: assert minimal outputs; chain by ref_id
    ├── test_multi_artifact_concat.py         # UPDATE: same
    └── test_*_live.py                        # UPDATE: relax uri requirement; use artifact_info when needed
```

## Implementation Phases (TDD)

### Phase 1 — Tests for new behavior (RED)
1. Add unit tests for `RunResponseSerializer`:
   - minimal excludes `session_id`, excludes `log_ref` on success, strips `workflow_record`, flattens summary fields
   - standard includes trimmed ref + metadata but no `file_metadata`
   - full includes `workflow_record` and `log_ref` on success
   - failed/validation_failed always include `log_ref`
   - channel_names truncation (>10)
2. Add unit/contract tests for `ArtifactRef` dump cleanup:
   - no `None` fields serialized
   - no empty `checksums: []`
   - no top-level `ndim/dims/shape/dtype/physical_pixel_sizes`
3. Update smoke assertions to accept minimal output (don’t require `uri`).

### Phase 2 — ArtifactRef model cleanup (GREEN)
1. Update `src/bioimage_mcp/artifacts/models.py`:
   - Remove top-level `ndim`, `dims`, `shape`, `dtype`, `physical_pixel_sizes` from `ArtifactRef`
   - Simplify `validate_dimension_metadata()` to validate only against `metadata`
   - Implement a controlled `model_dump()` override:
     - `exclude_none=True` always
     - post-process to drop empty `checksums` and empty `metadata`
2. Update artifact creation sites:
   - `src/bioimage_mcp/artifacts/store.py`: stop passing removed fields; ensure metadata contains dimension info
   - `src/bioimage_mcp/api/execution.py`: memory artifact creation should not set removed fields
3. Update `src/bioimage_mcp/api/artifacts.py` to read `dims/ndim` from `ref.metadata`.

### Phase 3 — Verbosity-aware response serialization (GREEN)
1. Create `src/bioimage_mcp/api/serializers.py`:
   - `RunResponseSerializer.serialize(result: dict, *, fn_id: str, verbosity: str) -> dict`
   - helpers:
     - `_artifact_minimal(ref_dict) -> dict`
     - `_artifact_standard(ref_dict) -> dict`
     - `_strip_file_metadata(metadata_dict) -> dict`
     - `_maybe_truncate_channel_names(list) -> list`
     - `_size_mb(size_bytes) -> float`
2. Ensure filtering rules:
   - remove `outputs["workflow_record"]` unless `verbosity == "full"`
   - remove top-level `log_ref` on success unless `full`
   - include `log_ref` on non-success regardless of verbosity
   - omit empty warnings
   - do not return `summary` or inline `content`

### Phase 4 — MCP tool integration (GREEN)
1. Update `src/bioimage_mcp/api/server.py`:
   - Add `verbosity: Literal["minimal","standard","full"] = "minimal"` to `run()` tool signature
   - Build response via serializer
   - Rename `id` → `fn_id` and drop `session_id` from `run` tool output

### Phase 5 — Chaining safety & smoke/integration alignment (GREEN)
1. Update input resolution in `ExecutionService.run_workflow`:
   - Extend `_resolve_input_ref` to handle dict values:
     - if `{"ref_id": "..."}` present but `uri` missing (or empty), inflate to canonical artifact ref from memory/artifact store
2. Update smoke tests to chain by `ref_id` strings and/or rely on inflation behavior.
3. Where tests need filesystem paths, call `artifact_info(ref_id)` to retrieve `uri` explicitly.

## Verification Commands

```bash
# Unit + contract tests for core logic
pytest tests/unit/ tests/contract/ -v

# Smoke tests (minimal surface)
pytest tests/smoke/ -m smoke_minimal -v

# Lint/format
ruff check .
ruff format --check .
```

## Notes / Edge Cases

- **Memory artifacts**: keep `uri` for `mem://` and `obj://` artifacts at all verbosity levels.
- **Multi-output functions**: apply per-output summarization; never assume a single primary output.
- **Large `channel_names`**: truncate to 10 at `minimal`/`standard`.
- **OME XML**: keep in stored metadata, but exclude from `run` responses except `full`.
- **`status()` tool**: intentionally unchanged for now; it remains the way to fetch full run outputs when needed.
