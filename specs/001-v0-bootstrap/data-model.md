# Phase 1 Data Model: v0.0 Bootstrap

This document identifies core entities needed to satisfy `specs/001-v0-bootstrap/spec.md` for v0.0.

## Entity: Config

Layered YAML configuration (global + local) controlling tool discovery roots and filesystem policies.

**Identity**: derived (not stored as a DB row)

**Fields**
- `config_version: str` (future-proofing)
- `artifact_store_root: str` (directory)
- `tool_manifest_roots: str[]` (directories)
- `fs_allowlist_read: str[]`
- `fs_allowlist_write: str[]`
- `fs_denylist: str[]`
- `default_pagination_limit: int`
- `max_pagination_limit: int`

**Validation rules**
- Roots must be absolute, normalized paths.
- Denylist always overrides allowlists.
- Writes must be restricted at least to artifact root + explicitly configured export roots.

## Entity: ToolManifest

File-based declaration of a tool pack.

**Identity**
- `manifest_path: str` (absolute path)
- `manifest_checksum: str` (sha256 of manifest file bytes)

**Fields**
- `manifest_version: str` (schema version)
- `tool_id: str` (stable identifier)
- `tool_version: str` (SemVer)
- `env_id: str` (e.g., `bioimage-mcp-base`)
- `entrypoint: str` (shim entrypoint, e.g., module or script path)
- `python_version?: str` (tool env python constraint)
- `platforms_supported: str[]` (e.g., `linux-64`)
- `functions: Function[]`

**Validation rules**
- `tool_id` unique across all discovered manifests.
- `env_id` must start with `bioimage-mcp-`.
- `entrypoint` must be present and non-empty.
- Invalid manifests are excluded from discovery results and produce diagnostics.

## Entity: Tool

A discoverable unit representing an installed/available tool pack.

**Identity**
- `tool_id: str`

**Fields**
- `name?: str`
- `description?: str`
- `tool_version: str`
- `env_id: str`
- `installed: bool`
- `available: bool`
- `functions: FunctionSummary[]` (summary-only for list views)

**Relationships**
- Tool is derived from exactly one ToolManifest (source of truth).

## Entity: Function

A callable operation exposed by a tool.

**Identity**
- `fn_id: str` (stable identifier; unique across registry)

**Fields**
- `tool_id: str`
- `name: str`
- `description: str`
- `tags: str[]`
- `inputs: Port[]`
- `outputs: Port[]`
- `params_schema: object` (JSON Schema-ish; full schema returned only via describe)
- `resource_hints?: {cpu?: int, gpu?: bool, memory_gb?: float}`

**Validation rules**
- `fn_id` unique across all tools.
- Ports must be typed with canonical artifact types.

## Entity: Port

Typed input or output connector.

**Fields**
- `name: str`
- `artifact_type: str` (canonical: `BioImageRef`, `LabelImageRef`, `TableRef`, `ModelRef`, `LogRef`)
- `format?: str` (e.g., `OME-TIFF`, `OME-Zarr`)
- `required: bool`

## Entity: ArtifactRef (base)

Typed, file-backed artifact reference.

**Identity**
- `ref_id: str`

**Fields**
- `type: str`
- `uri: str` (v0.0: `file://` only)
- `format: str`
- `mime_type: str`
- `size_bytes: int`
- `checksums: {algorithm: str, value: str}[]`
- `created_at: str` (RFC3339)
- `metadata: object` (type-specific)

**Validation rules**
- `uri` must resolve under configured allowlisted roots for reads/writes.
- Checksums must be present for produced artifacts.

### Artifact subtype: BioImageRef

**metadata (minimum)**
- `axes: str` (e.g., `TCZYX`)
- `shape: int[]`
- `dtype: str`
- `channel_names?: str[]`
- `physical_pixel_sizes?: {X?: float, Y?: float, Z?: float}`

### Artifact subtype: LogRef

**metadata (minimum)**
- `stream?: "stdout"|"stderr"|"combined"`
- `exit_code?: int`
- `truncated?: bool`

## Entity: Run

A single execution attempt of a function/workflow.

**Identity**
- `run_id: str`

**Fields**
- `status: "queued"|"running"|"succeeded"|"failed"|"cancelled"`
- `created_at: str` (RFC3339)
- `started_at?: str`
- `ended_at?: str`
- `workflow_spec: object` (v0.0: can be 1-step)
- `inputs: {name: ArtifactRef} map`
- `params: object`
- `outputs?: {name: ArtifactRef} map`
- `log_ref: LogRef`
- `error?: {code: str, message: str, details?: object}`
- `provenance: Provenance`

**State transitions**
- `queued -> running -> succeeded|failed|cancelled`

## Entity: Provenance

Minimum provenance needed for reproducibility.

**Fields**
- `tool_id: str`
- `tool_version: str`
- `fn_id: str`
- `env_id: str`
- `env_lock_hash?: str` (if available)
- `input_checksums: {input_name: checksum} map`
- `output_checksums?: {output_name: checksum} map`
- `parameters_hash?: str` (stable hash of params for caching later)
- `host: {platform: str, python: str}`

## SQLite Index (MVP)

SQLite is used as an index for discovery + lookup.

Suggested tables (conceptual):
- `tools(tool_id PRIMARY KEY, tool_version, env_id, description, manifest_path, installed, available)`
- `functions(fn_id PRIMARY KEY, tool_id, name, description, tags_json, inputs_json, outputs_json)`
- `artifacts(ref_id PRIMARY KEY, type, uri, format, mime_type, size_bytes, checksums_json, metadata_json, created_at)`
- `runs(run_id PRIMARY KEY, status, created_at, started_at, ended_at, workflow_spec_json, inputs_json, params_json, outputs_json, log_ref_id, error_json, provenance_json)`

Validation rules:
- Ensure indexes for `functions(tags_json)` and keyword search fields to meet discovery latency targets.
