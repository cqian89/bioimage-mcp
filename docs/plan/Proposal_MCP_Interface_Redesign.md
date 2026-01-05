# Proposal: MCP Interface Redesign (Clean Surface)

**Status**: Draft  
**Created**: 2026-01-04  
**Context**: Improve LLM usability, reduce bloat, and fix contract inconsistencies

## 1. Executive Summary

BioImage-MCP’s current MCP-facing surface mixes multiple concepts (catalog browsing, function introspection, execution, artifact I/O, session/workflow recording) with inconsistent naming and partially redundant/broken tools.

This proposal defines a **small, consistent MCP tool surface** that:
- keeps discovery compact and paginated (anti-context-bloat)
- exposes rich but bounded metadata needed for LLMs to call tools correctly
- unifies identifiers and schemas (no more `full_path` vs `fn_id` mismatches)
- consolidates execution to a single pathway (no divergent `run_function` vs `run_workflow` behavior)
- makes errors actionable (structured validation errors + “what to do next” hints)

Backward compatibility is intentionally not a priority.

## 2. Goals and Non-Goals

### 2.1 Goals

1. **LLM-friendly discovery**
   - LLM can answer: “what exists?”, “what takes a BioImageRef?”, “what should I call next?” with few calls.
   - List operations expose **child counts** so the LLM can decide whether to expand a node.

2. **Consistent contracts**
   - One identifier per thing.
   - JSON Schema types match reality (numbers are numbers; booleans are booleans).
   - Separation between:
     - artifact ports (`inputs`/`outputs`), and
     - JSON parameters (`params`).

3. **Actionable errors**
   - Validation errors should include machine-parseable paths and human-readable fixes.

4. **No bloat**
   - Remove tools that overlap, are broken, or are only internal implementation details.

### 2.2 Non-goals

- Returning large arrays or binary payloads inside MCP messages.
- Providing full filesystem access to callers.
- Supporting legacy naming or formats.

## 3. Findings From Live Server Interaction

This proposal is based on directly calling the existing BioImage-MCP server tools and observing responses.

### 3.1 Naming/Concept confusion

- `list_tools` actually lists a **catalog** of environments/packages/functions.
- `describe_function` only describes functions, but callers also need descriptions of environments/packages/modules.

### 3.2 Missing information for navigation

- Catalog nodes only provide `has_children: true|false`, but not **how many children**.
- LLMs need child counts to avoid expensive expansion and to decide whether to use search instead.

### 3.3 Schema correctness issues

- Some parameter schemas report incorrect JSON Schema types (e.g. numeric defaults paired with `type: "string"`).
- Some functions appear to duplicate artifact ports inside `schema.properties` (e.g. an `image` property even though `inputs.image` is a `BioImageRef`).

### 3.4 Execution/dry-run inconsistencies

- A “dry run” path should validate required inputs the same way as a real run.
- Current behavior can accept missing required ports under dry-run, which misleads an LLM.

### 3.5 Broken or unclear tools

- `describe_tool` appears non-functional (tool id space unclear; repeated calls error).
- `run_workflow` behaves differently from `run_function` and appears to support only a single step, with adapter resolution failures in cases where `run_function` can execute.

### 3.6 Artifact export usability

- `export_artifact` can fail with “Path not under any allowed write root” but does not report what the allowed roots are.
- The destination path is on the **server-side filesystem**, which must be explicit in the API contract.

## 4. Proposed Clean MCP Surface

The MCP surface should be **7 tools** total. The names are intentionally short and consistent.

### 4.1 `list` (replaces `list_tools`)

**Purpose**: Browse environments/packages/modules/functions.

**Request**
```json
{
  "path": "base.skimage.filters",
  "cursor": null,
  "limit": 50,
  "types": ["environment", "package", "module", "function"],
  "include_counts": true
}
```

**Response**
```json
{
  "items": [
    {
      "id": "base.skimage.filters.gaussian",
      "type": "function",
      "name": "gaussian",
      "summary": "Apply a Gaussian filter to an image to reduce noise and detail.",
      "io": {
        "inputs": [{"name": "image", "type": "BioImageRef", "required": true}],
        "outputs": [{"name": "output", "type": "BioImageRef"}]
      }
    },
    {
      "id": "base.skimage.filters",
      "type": "module",
      "name": "filters",
      "summary": "skimage.filters",
      "children": {"total": 46, "by_type": {"function": 46}}
    }
  ],
  "next_cursor": "...",
  "expanded_from": "base.skimage.filters"
}
```

**Key changes**
- `id` is the only identifier.
- `children.total` and `children.by_type` replace `has_children`.
- Optional lightweight `io` summary for functions prevents extra `describe` calls.

### 4.2 `describe` (replaces `describe_function`)

**Purpose**: Describe any catalog node.

- For environments/packages/modules: returns metadata + child counts + optional child preview.
- For functions: returns params schema, ports, hints, and examples.

**Request**
```json
{ "id": "base.skimage.filters.gaussian" }
```

**Response (function)**
```json
{
  "id": "base.skimage.filters.gaussian",
  "type": "function",
  "summary": "Apply a Gaussian filter to an image...",
  "tags": ["denoise", "smooth", "filter"],
  "inputs": {
    "image": {
      "type": "BioImageRef",
      "required": true,
      "hints": {
        "expected_axes": ["Y", "X"],
        "min_ndim": 2,
        "max_ndim": 3,
        "squeeze_singleton": true
      }
    }
  },
  "params_schema": {
    "type": "object",
    "properties": {
      "sigma": {"type": "number", "default": 1.0},
      "preserve_range": {"type": "boolean", "default": false}
    }
  },
  "outputs": {
    "output": {"type": "BioImageRef"}
  },
  "examples": [
    {
      "inputs": {"image": "<BioImageRef>"},
      "params": {"sigma": 1.5}
    }
  ],
  "next_steps": [
    {"id": "base.skimage.morphology.remove_small_objects", "reason": "Often follows denoising"}
  ]
}
```

**Key changes**
- **No artifact ports inside params schema**. Artifact ports live only under `inputs`/`outputs`.
- Correct JSON Schema types.
- Examples show how to structure `inputs` vs `params`.

### 4.3 `search` (replaces `search_functions`)

**Purpose**: Find functions quickly.

**Request**
```json
{
  "query": "threshold",
  "tags": ["segmentation"],
  "io_in": "BioImageRef",
  "io_out": "LabelImageRef",
  "limit": 20,
  "cursor": null
}
```

**Response**
```json
{
  "results": [
    {
      "id": "cellpose.eval",
      "type": "function",
      "name": "Cellpose Eval",
      "summary": "Core evaluation function for Cellpose models.",
      "tags": ["segmentation", "deep-learning"],
      "io": {
        "inputs": [{"name": "image", "type": "BioImageRef", "required": true}],
        "outputs": [{"name": "labels", "type": "LabelImageRef"}]
      },
      "score": 44.3,
      "match_count": 1
    }
  ],
  "next_cursor": null
}
```

**Key changes**
- Always include I/O summary in search results.
- Require exactly one of `query` or `keywords`. If missing, return a structured validation error.

### 4.4 `run` (replaces `run_function` and `run_workflow`)

**Purpose**: Execute exactly one function call.

**Request**
```json
{
  "id": "base.skimage.filters.gaussian",
  "inputs": {"image": "<BioImageRef>"},
  "params": {"sigma": 1.0},
  "session_id": null,
  "dry_run": false
}
```

**Response**
```json
{
  "session_id": "session_...",
  "run_id": "...",
  "status": "success",
  "id": "base.skimage.filters.gaussian",
  "outputs": {
    "output": {
      "ref_id": "...",
      "type": "BioImageRef",
      "uri": "file:///...",
      "mime_type": "image/tiff",
      "format": "OME-TIFF",
      "size_bytes": 1234567,
      "dims": ["Y", "X"],
      "ndim": 2,
      "dtype": "uint16",
      "shape": [1024, 1024]
    }
  },
  "warnings": [],
  "log_ref": {"ref_id": "...", "type": "LogRef"}
}
```

**Key changes**
- Single execution API. Multi-step workflows should be built via repeated `run` calls under a `session_id`.
- `dry_run=true` must perform full validation and return `status="validation_failed"` with details.
- Always return output artifact refs with bounded metadata (e.g. `ndim`, `dims`, `dtype`, `shape`, `size_bytes`).

### 4.5 `status` (replaces `get_run_status`)

**Purpose**: Poll a run.

**Request**
```json
{ "run_id": "..." }
```

**Response**
```json
{
  "run_id": "...",
  "status": "running",
  "progress": {"completed": 0, "total": 1},
  "outputs": {},
  "log_ref": {"ref_id": "...", "type": "LogRef"}
}
```

**Key changes**
- Include minimal progress fields for long-running tools.

### 4.6 `artifact_info` (replaces `get_artifact`)

**Purpose**: Retrieve artifact metadata; optionally preview small text artifacts.

**Request**
```json
{ "ref_id": "...", "text_preview_bytes": 4096 }
```

**Response**
```json
{
  "ref_id": "...",
  "type": "LogRef",
  "uri": "file:///...",
  "mime_type": "text/plain",
  "size_bytes": 123,
  "checksums": [{"algorithm": "sha256", "value": "..."}],
  "text_preview": "Traceback...\n"
}
```

**Key changes**
- `text_preview` is only present for safe text-like artifacts and is strictly size-bounded.

### 4.7 `session_export` (replaces `export_session`)

**Purpose**: Export a reproducible workflow record (steps, inputs/params, tool versions, lockfile hashes, timestamps).

**Request**
```json
{ "session_id": "session_..." }
```

**Response**
```json
{
  "session_id": "session_...",
  "workflow_ref": {"ref_id": "...", "type": "NativeOutputRef", "format": "workflow-record-json"}
}
```

**Key changes**
- Always exports a non-empty record if at least one call was attempted.
- Record includes failed attempts and marks the “canonical” successful steps.

## 5. What to Remove (Bloat)

### 5.1 Remove `describe_tool`

It is either non-functional or duplicates `describe` in a confusing way. If needed, keep it strictly internal.

### 5.2 Remove `activate_functions` / `deactivate_functions`

With a stable, wrapper-based interface (`list/search/describe/run`), clients can handle filtering and there is no need for dynamic tool registration complexity.

If selective exposure is still desired later for UI limits, introduce it as an optional `list` filter (e.g. `active_only=true`) rather than separate tools.

### 5.3 Remove `run_workflow`

Having two execution entry points invites divergence. Replace it with:
- `run` for single calls
- session accumulation for multi-step workflows

## 6. Error Model (Must-Have)

All tools should use the same structured error shape.

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Missing required input 'image'",
    "details": [
      {
        "path": "/inputs/image",
        "expected": "BioImageRef",
        "actual": "missing",
        "hint": "Provide a BioImageRef from a prior tool output"
      }
    ]
  }
}
```

Guidelines:
- `code` is stable and enumerable.
- `path` uses JSON Pointer.
- Include a short `hint` to make automated retries feasible.

## 7. Catalog Model and Identifiers

### 7.1 Node types

- `environment` (e.g. `base`, `cellpose`)
- `package` (Python top-level package in an environment)
- `module` (Python module/submodule)
- `function` (callable registry function)

### 7.2 Identifier rules

- Every node has exactly one stable `id`.
- For functions, `id` is the callable identifier used by `run`.
- `name` is display-only.

This removes the current confusion between `full_path`, `name`, and `fn_id`.

## 8. Artifact Export and Path Semantics

If `export_artifact` remains a tool, it must be explicit that:
- destination paths are resolved on the **server filesystem**
- writes are restricted to configured allowlisted roots

When export is denied, return:
- the attempted path
- the configured allowed roots (or a redacted summary)

Preferably:
- expose artifact contents as **MCP resources** (read-only) where clients can fetch bytes
- keep tool-based export only for server-local persistence

## 9. Implementation Plan (Codebase-Oriented)

1. **Define new Pydantic models** for catalog nodes, search results, params schemas, and errors.
2. **Implement new API handlers** under `src/bioimage_mcp/api/`:
   - `list`, `describe`, `search`, `run`, `status`, `artifact_info`, `session_export`.
3. **Delete/retire** old handlers and any supporting code paths (`describe_tool`, `run_workflow`, activation tools).
4. **Fix schema generation**:
   - correct JSON schema types
   - ensure `inputs/outputs` are never duplicated inside params schema
5. **Add contract tests** in `tests/contract/` to lock:
   - pagination behavior
   - schema correctness
   - error shapes
   - stable identifier rules
6. **Add integration tests** in `tests/integration/` to verify:
   - a simple `run` produces artifacts with expected metadata
   - `session_export` produces a non-empty record

## 10. Acceptance Criteria

- A new user/LLM can discover → describe → run a tool with ≤3 calls for common tasks.
- `list` returns child counts for every non-leaf node.
- `describe` returns correct JSON Schema types and separates artifact ports from params.
- `dry_run` validates required inputs/params identically to real execution.
- One execution tool exists (`run`), and it behaves consistently across environments.
- Errors are structured and include fix hints.
