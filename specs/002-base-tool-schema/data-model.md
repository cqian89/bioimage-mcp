# Data Model: Base Tool Schema Expansion

**Date**: 2025-12-19
**Status**: Draft

This document defines the key entities and persistence shapes needed to support on-demand schema enrichment, a richer base toolkit, and live workflow validation.

## 1. Core Entities

### 1.1 Tool Pack (`ToolManifest`)

**Purpose**: Represents a collection of executable functions in a single isolated environment.

**Key fields** (see `src/bioimage_mcp/registry/manifest_schema.py`):
- `tool_id: str` (e.g. `tools.base`, `tools.cellpose`)
- `tool_version: str` (semver-like string)
- `env_id: str` (must start with `bioimage-mcp-`)
- `entrypoint: str` (tool subprocess entrypoint)
- `functions: list[Function]`
- `manifest_path: Path` (absolute)
- `manifest_checksum: str` (used to detect changes)

**Relationships**:
- 1 Tool Pack → N Functions

### 1.2 Function (`Function`)

**Purpose**: One addressable operation in a tool pack.

**Key fields**:
- `fn_id: str` (globally unique, e.g. `base.gaussian`, `cellpose.segment`)
- `tool_id: str` (owning tool)
- `name: str`, `description: str`, `tags: list[str]`
- `inputs: list[Port]`, `outputs: list[Port]`
- `params_schema: dict` (may be minimal in manifest)
- `introspection_source: str | None` (`python_api`, `argparse`, `manual`, or `None`)

**Validation rules**:
- Input/output ports must reference known artifact types (canonical: `BioImageRef`, `LabelImageRef`, `LogRef`, `NativeOutputRef`).
- `params_schema` MUST be a JSON-Schema-like object (`type: object`, `properties`, `required`) when returned to clients via `describe_function`.

### 1.3 Artifact Reference (`ArtifactRef`)

**Purpose**: Typed, file-backed references for all inter-tool I/O (no large payloads in MCP messages).

**Key fields** (see `src/bioimage_mcp/artifacts/models.py`):
- `ref_id: str`
- `type: str`
- `uri: str` (file-backed URI)
- `format: str` (open/extensible, e.g. `OME-Zarr`, `OME-TIFF`, `workflow-record-json`)
- `mime_type: str`, `size_bytes: int`, `checksums: list`, `metadata: dict`, `created_at: str`

### 1.4 Workflow Run (`Run`) and Workflow Record (`WorkflowRecord`)

**Purpose**: Capture reproducible execution of multi-step workflows.

**Run fields** (see `src/bioimage_mcp/runs/models.py`):
- `run_id`, `status`, timestamps
- `workflow_spec`, `inputs`, `params`, `outputs`
- `log_ref_id`, `error`, `provenance`
- `native_output_ref_id` (link to a `workflow-record-json` artifact)

**Run status transitions**:
- `queued` → `running` → (`succeeded` | `failed` | `cancelled`)

**WorkflowRecord fields**:
- `schema_version`, `run_id`, `created_at`
- `workflow_spec`, `inputs`, `params`, `outputs`, `provenance`
- optional `tool_manifests` snapshots and `env_fingerprint`


## 2. Schema Cache Model (Local JSON)

### 2.1 Schema Cache File

**Purpose**: Persist enriched parameter schemas returned by tool-side `meta.describe` so repeated `describe_function(fn_id)` calls do not re-run expensive introspection.

**Proposed file path**: `${artifact_store_root}/state/schema_cache.json`

**Top-level structure** (versioned for forward compatibility):
```json
{
  "schema_version": "0.1",
  "tools": {
    "<tool_id>@<tool_version>": {
      "functions": {
        "<fn_id>": {
          "params_schema": { "type": "object", "properties": {}, "required": [] },
          "introspection_source": "python_api",
          "introspected_at": "2025-12-19T00:00:00Z"
        }
      }
    }
  }
}
```

### 2.2 SchemaCacheEntry

**Key fields**:
- `tool_id: str`
- `tool_version: str`
- `fn_id: str`
- `params_schema: dict`
- `introspection_source: str`
- `introspected_at: str` (ISO 8601)

**Validation rules**:
- Cache entries are **version-keyed**: a `tool_version` mismatch MUST be treated as stale.
- `params_schema` MUST be JSON-serializable.

### 2.3 Cache Invalidation

Invalidate cached schemas when any of these change:
- `tool_version` changes (primary rule per FR-004)
- `manifest_checksum` changes (optional enhancement; catches manifest edits without version bump)


## 3. Notes on Coexistence with SQLite

The repo currently includes a SQLite `schema_cache` table used for meta.describe caching. This feature’s requirement explicitly calls for a **local JSON file** cache. Design options:
- JSON as the canonical cache (and SQLite cache deprecated or unused for schemas)
- JSON + SQLite dual-write (JSON required for compliance; SQLite retained for performance)

The implementation plan will pick the minimal option that satisfies FR-003 while keeping behavior deterministic.
