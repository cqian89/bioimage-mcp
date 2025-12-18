# Phase 0 Research: v0.0 Bootstrap

This document consolidates key design decisions for v0.0 using only repository context:
- `specs/001-v0-bootstrap/spec.md`
- `initial_planning/Bioimage-MCP_PRD.md`
- `initial_planning/Bioimage-MCP_ARCHITECTURE.md`
- `.specify/memory/constitution.md`

No open questions remain from the plan’s Technical Context.

## MCP Surface (Discovery + Execution)

### Decision
Expose a minimal, stable, summary-first MCP surface that supports the three v0.0 user stories:
- Discovery via paginated list/search/describe
- Execution via a single “run workflow” entrypoint (a workflow is a 1-step linear plan in v0.0)
- Artifact metadata + export

### Rationale
- Aligns with PRD “constant LLM-facing API” while staying compact.
- Enforces anti-context-bloat: clients must search → describe → run.
- Keeps room for v0.1+ multi-step workflows without adding a second execution API and later deprecating it.

### Alternatives considered
- `run_function(fn_id, ...)` in v0.0: simpler, but introduces likely deprecation when workflow recording/replay becomes a first-class primitive.
- Returning full schemas in list/search: rejected due to context bloat and constitution Principle I.

### Proposed operations (conceptual)
- `list_tools(cursor?, limit?) -> {tools[], next_cursor?}`
- `describe_tool(tool_id) -> {tool, functions[]}`
- `search_functions(query, tags?, io_in?, io_out?, cursor?, limit?) -> {functions[], next_cursor?}`
- `describe_function(fn_id) -> {function, full_schema}`
- `run_workflow(spec, inputs, run_opts?) -> {run_id, status}`
- `get_run_status(run_id) -> {status, outputs, log_ref, error?}`
- `get_artifact(ref_id) -> {artifact_ref}`
- `export_artifact(ref_id, dest_uri|dest_path) -> {exported_ref?, status}`

## Pagination Strategy

### Decision
Use an opaque cursor (`cursor` / `next_cursor`) for pagination rather than offset-based pagination.

### Rationale
- More stable under catalog changes (tools added/removed).
- Easy to keep response sizes bounded by default.

### Alternatives considered
- Offset/limit: simpler to implement but more error-prone under mutation and can be slower at scale.

## Artifact Reference Schema

### Decision
Use typed, file-backed artifact references for all I/O and logs. v0.0 is local-first: `file://` URIs only.

### Rationale
- Constitution Principle III requires file-backed refs and forbids binary payloads in MCP messages.
- Artifact refs must carry enough metadata to support planning/validation without downloading the artifact.

### Alternatives considered
- URI-only references: rejected because clients need axes/shape/channel info for planning.
- Embedding pixel data: rejected due to context bloat and protocol scalability.

### Proposed base schema
- `ref_id: str` (stable ID within the artifact store)
- `type: str` (one of `BioImageRef`, `LabelImageRef`, `TableRef`, `ModelRef`, `LogRef`)
- `uri: str` (v0.0: `file://` only)
- `format: str` (e.g., `OME-Zarr`, `OME-TIFF`, `text`)
- `mime_type: str` (e.g., `application/zarr+ome`, `image/tiff`, `text/plain`)
- `size_bytes: int`
- `checksums: {algorithm: str, value: str}[]` (at minimum: SHA-256)
- `created_at: str` (RFC3339)
- `metadata: object` (type-specific)

### Minimal metadata requirements
- `BioImageRef`:
  - `axes: str` (e.g., `TCZYX`)
  - `shape: int[]` (aligned with `axes`)
  - `dtype: str`
  - `channel_names?: str[]`
  - `physical_pixel_sizes?: {X?: float, Y?: float, Z?: float}`
- `LogRef`:
  - `stream?: "stdout"|"stderr"|"combined"`
  - `exit_code?: int`
  - `truncated?: bool`

### Checksum strategy
- Regular files: SHA-256 over file bytes.
- Directory artifacts (e.g., `.ome.zarr`):
  - v0.0: compute a deterministic “tree hash” SHA-256 by walking files in sorted path order and hashing `(relative_path + file_bytes)`.
  - Record algorithm explicitly (e.g., `sha256-tree`) so it’s not confused with a single-file digest.

## Tool Manifest Validation (YAML + Pydantic 2)

### Decision
Validate YAML tool manifests by parsing YAML to a dict and validating with Pydantic v2 models; index only valid manifests.

### Rationale
- Meets FR-004 (YAML + Pydantic 2 schema validation).
- Supports clear diagnostics: invalid manifests are excluded from discovery, but validation errors are surfaced.

### Alternatives considered
- JSON manifests: rejected for poorer human ergonomics.
- “Best-effort” manifests: rejected because silent coercions lead to unstable discovery and hard-to-debug failures.

### Versioning strategy
- Include a `manifest_version` field for schema versioning.
- Include a separate `tool_version` field (SemVer) for the tool pack itself.
- Add fields compatibly (backward-compatible defaults) to preserve stable discovery/describe behavior.

### Invalid manifest handling
- Exclude invalid entries from list/search results.
- Record diagnostics as structured data (per-manifest): `{path, tool_id?, errors[]}`.
- Surface diagnostics via `doctor` and via server logs; optionally expose a bounded diagnostics endpoint/tool.

## Built-in Functions: Gaussian Blur + Convert to OME-Zarr

### Decision
Implement two built-in functions as part of a “base tool pack” executed via the same shim + subprocess boundary as external tools, typically in `bioimage-mcp-base`.

- Gaussian blur: use a standard scientific imaging library (`scipy.ndimage` or `scikit-image`) available in the base env.
- Conversion: use `bioio` for reading and `ngff-zarr` for writing OME-Zarr.

### Rationale
- Preserves the isolation boundary even for “built-ins”, reducing special-casing.
- Standardizes artifact I/O and provenance recording for all functions.

**Format strategy note**: The project is pivoting to OME-TIFF as the preferred default intermediate in v0.1.

### Alternatives considered
- Run built-ins in-process (core server env): rejected because it couples core env deps to imaging stacks.

### I/O expectations
- Inputs and outputs are always `BioImageRef` artifact references.
- Gaussian blur output SHOULD be OME-Zarr in v0.0.
- Convert-to-OME-Zarr always outputs OME-Zarr.
- v0.1: switch default built-in/pipeline outputs to OME-TIFF; keep OME-Zarr as an optional/future format.

### Validations & common failure modes
- Validate input file existence/readability and allowlisted roots.
- Validate output paths are within allowlisted write roots.
- Validate dimensionality/axes: blur must not blur non-spatial axes; define sigma semantics (per-axis or spatial-only).
- Handle disk-full and permission errors; always write a `LogRef` on failure.
- Ensure metadata propagation: axes, pixel sizes, channels preserved when writing outputs.
