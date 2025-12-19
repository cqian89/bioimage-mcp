# Phase 1 Data Model: v0.1 First Real Pipeline (Cellpose)

**Branch**: `001-cellpose-pipeline`  
**Date**: 2025-12-18  
**Spec**: `/mnt/c/Users/meqia/bioimage-mcp/specs/001-cellpose-pipeline/spec.md`

This document describes the core entities involved in the v0.1 pipeline as they exist (or should exist) in the current codebase.

## Entities

### Artifact Reference (`ArtifactRef`)

- Purpose: Typed, file-backed pointer used for all inter-tool I/O.
- Storage: SQLite row in `artifacts` table + payload at `artifact_store_root/objects/<ref_id>`.
- Canonical shape (wire payload): `src/bioimage_mcp/artifacts/models.py::ArtifactRef`

Fields:
- `ref_id` (string, required): Stable identifier for lookup/export.
- `type` (string, required): Semantic role, e.g. `BioImageRef`, `LabelImageRef`, `LogRef`, `NativeOutputRef`.
- `uri` (string, required): `file://...` URI to on-disk artifact payload.
- `format` (string, required): On-disk format name. **Open and extensible** — values are tool-dependent (e.g., `OME-TIFF`, `workflow-record-json`, `cellpose-seg-npy`).
- `mime_type` (string, required): Derived from `type` + `format`.
- `size_bytes` (int, required): Size of stored payload.
- `checksums` (list, optional): At least `sha256` for files, `sha256-tree` for directories.
- `created_at` (string, required): ISO timestamp.
- `metadata` (dict, optional): For images, minimal metadata (axes, etc.) extracted on import.

Validation rules:
- `uri` MUST be a `file://...` URI pointing within `artifact_store_root`.
- `type` MUST be one of the system’s canonical artifact types (currently treated as stringly-typed in code; design assumes canonical set).

### Run (`Run`)

- Purpose: Record a single workflow execution instance and provide user-retrievable status + outputs + logs.
- Storage: SQLite row in `runs` table.
- Canonical shape: `src/bioimage_mcp/runs/models.py::Run`

Fields:
- `run_id` (string, required)
- `status` (string, required): `queued|running|succeeded|failed|cancelled` (as used by `RunStore`)
- `created_at`, `started_at`, `ended_at` (strings)
- `workflow_spec` (dict): User-submitted workflow spec (linear in v0.1)
- `inputs` (dict), `params` (dict): Captured for provenance and replay.
- `outputs` (dict|null): Mapping output name → serialized `ArtifactRef` payload.
- `log_ref_id` (string): Reference to a `LogRef` artifact.
- `error` (dict|null): Structured error details.
- `provenance` (dict): Minimal provenance, intended to expand with tool/env fingerprinting.

State transitions:
- `queued` → `running` → `succeeded|failed`
- `queued|running` → `cancelled` (future)

Validation rules:
- Every run MUST have `log_ref_id` (FR-003).
- On failure, run MUST still be retrievable and include `error` + `log_ref_id`.

### Workflow Record Artifact (`ArtifactRef` where `type="NativeOutputRef"` and `format="workflow-record-json"`)

- Purpose: File-backed JSON document capturing executed steps, parameters, tool identity/version, and environment fingerprint for later replay (FR-004/FR-005).
- Storage: As an artifact (`ArtifactRef`) pointing to a JSON file payload.
- Format: `workflow-record-json` (and `mime_type="application/json"`).

Minimum JSON fields (proposed contract for v0.1):
- `schema_version` (string)
- `created_at` (string)
- `run_id` (string)
- `steps` (array): each with `fn_id`, `tool_id`, `params`, `inputs` (artifact refs), `outputs` (artifact refs)
- `tool_manifests` (array or map): manifest checksums/versions used in the run
- `env_fingerprint` (object): best-effort env manager + env id + Python version

Notes:
- Current code stores `workflow_spec` in the run record but does not yet emit a separate workflow record artifact; Phase 2 planning should define where this is created in the execution path.

### Label Image (`ArtifactRef` where `type="LabelImageRef"`)

- Purpose: Instance segmentation labels output; single-channel integer image with `0=background`, `1..N=instances`.
- Storage: File-backed image payload (default `OME-TIFF`).
- Validation rules:
  - Pixel type integer (uint16/uint32 preferred).
  - Single channel, 2D or 3D, depending on input; instances encoded in pixel values.

## Relationships

- A `Run` has exactly one `log_ref_id` → an `ArtifactRef(type="LogRef")`.
- A `Run` may have many output artifacts (stored as serialized `ArtifactRef` objects in `Run.outputs`).
- A `Workflow Record Artifact` references a prior `Run` via `run_id` and links steps to input/output artifact refs.

