# Phase 0 Research: v0.1 First Real Pipeline (Cellpose)

**Branch**: `001-cellpose-pipeline`  
**Date**: 2025-12-18  
**Spec**: `/mnt/c/Users/meqia/bioimage-mcp/specs/001-cellpose-pipeline/spec.md`

This document resolves Phase 0 unknowns and records decisions with rationale and alternatives.

## 1) Artifact Reference wire format

- Decision: Use `src/bioimage_mcp/artifacts/models.py::ArtifactRef` as the canonical v0.1 wire format for artifact references, surfaced to clients via `.model_dump()` payloads.
- Rationale: The model already matches the spec clarifications: structured object with a `file://...` URI (`Path(...).as_uri()`), plus metadata and checksums. The `ArtifactStore` already persists and returns this shape consistently.
- Alternatives considered:
  - Raw `file://` strings only: rejected because metadata (type, mime, checksums, image axes) is required for validation and compatibility checks.
  - Ad-hoc dicts per-tool: rejected because it would be unstable and violate "stable, versioned schemas".

Notes:
- `ArtifactRef.metadata` is used for image metadata (see `src/bioimage_mcp/artifacts/metadata.py` and `ArtifactStore.import_file()`).
- Tools currently return `{type, format, path}` and the core wraps them into `ArtifactRef` entries.

## 2) Artifact store layout + configuration

- Decision: Artifact payloads live under `artifact_store_root/objects/<ref_id>`; tool work areas currently use `artifact_store_root/work/runs/`.
- Rationale: This is already implemented in `src/bioimage_mcp/artifacts/store.py` and `src/bioimage_mcp/api/execution.py`. Keeping this stable aligns with reproducibility and makes it easy to reference artifacts by ID.
- Alternatives considered:
  - Per-run directory as primary storage: rejected for MVP because the store already provides ID-addressable objects + SQLite indexing; per-run structuring can be layered via metadata/provenance later.

Open items deferred to Phase 2 planning (not required to finish Phase 0):
- Whether we should create a per-run subdirectory under `work/runs/<run_id>/` (currently it is a shared directory).

## 3) Filesystem allowlists

- Decision: Enforce filesystem policy via `src/bioimage_mcp/config/fs_policy.py::assert_path_allowed()` using `Config.fs_allowlist_read`, `Config.fs_allowlist_write`, and `Config.fs_denylist`. The artifact store itself is implicitly trusted for reads when source paths are within `artifact_store_root`.
- Rationale: This is already the central policy hook used by `ArtifactStore.import_file()`, `import_directory()`, and `export()`. It implements deny-first then allow-by-operation.
- Alternatives considered:
  - No policy / "best effort": rejected because FR-009 requires enforcement and the constitution requires explicit access policy.
  - Only enforce on export: rejected because reads must also be constrained.

Notes:
- `ArtifactStore.import_file()` only checks allowlists when importing from outside `artifact_store_root` (to avoid self-blocking when moving artifacts around).

## 4) Tool registry + adding a new tool pack

- Decision: Add Cellpose as a new tool manifest under `tools/` using the existing manifest schema (`src/bioimage_mcp/registry/manifest_schema.py`) and subprocess entrypoint protocol (`src/bioimage_mcp/runtimes/executor.py` + JSON stdin/stdout used by `tools/builtin/bioimage_mcp_builtin/entrypoint.py`).
- Rationale: This matches Constitution Principle II (isolated tool execution) and keeps the MCP surface stable: new capabilities are discovered via manifests and invoked via `fn_id` without bespoke in-core integrations.
- Alternatives considered:
  - Embed Cellpose directly in core server environment: rejected (heavy deps; violates Principle II).
  - Special-case Cellpose inside `ExecutionService`: rejected (bespoke glue; hurts scalability and stability).

Protocol constraints observed:
- Tool entrypoints read JSON from stdin and write a JSON response to stdout.
- Response should include `ok`, `outputs` and may include `error` and `log`.
- Core currently expects outputs to provide `path` (string), and optionally `type` + `format`.

## 5) Cellpose environment packaging

- Decision: Package Cellpose as an isolated environment referenced by `env_id` in the tool manifest. Keep the environment definition under `envs/` (e.g., `envs/bioimage-mcp-cellpose.yaml`) and ensure the env name starts with `bioimage-mcp-` to satisfy `ToolManifest.env_id` validation.
- Rationale: The runtime already supports env-managed subprocess execution via `micromamba`/`conda` detection (`src/bioimage_mcp/bootstrap/env_manager.py`), and manifest schema enforces a consistent `env_id` prefix.
- Alternatives considered:
  - Pip/venv in-place under `tools/`: rejected because the architecture and constitution explicitly prefer per-tool conda/micromamba envs for reproducibility and isolation.

NEEDS CLARIFICATION (to resolve in Phase 2 planning, not blocking Phase 1 design docs):
- Exact dependency pins and whether to use `conda-lock` in v0.1 (constitution prefers pinned envs; the current repo may not yet include lock tooling).

## 6) OME-TIFF vs OME-Zarr for v0.1

- Decision: For v0.1 pipeline outputs, prefer OME-TIFF as the default output format, matching the feature spec "OME-TIFF pivot" requirement. Keep existing OME-Zarr support in built-ins as-is (it's already present), but do not require it for the new pipeline.
- Rationale: The spec explicitly calls for OME-TIFF by default for interoperability; the artifact store already guesses TIFF mime types and supports file artifacts well.
- Alternatives considered:
  - Default to OME-Zarr: rejected because the spec defers it and because file-backed single-image workflows are simplest with TIFF for v0.1.
  - Support both with automatic branching: rejected for v0.1 scope; increases complexity and surface area.

## 7) Compatibility validation approach (workflow gating)

- Decision: Validate workflow step I/O compatibility using the function's manifest ports (`Function.inputs`/`outputs`) before starting subprocess execution.
- Rationale: FR-006 requires rejecting incompatible workflows before any tool execution; manifest ports are the authoritative contract.
- Alternatives considered:
  - Let tool fail at runtime: rejected (doesn't satisfy FR-006).
  - Validate only by runtime inspection of produced artifacts: rejected (too late; execution already started).

## 8) Cellpose API vs CLI for Bioimage-MCP tool execution

Context: In v0.1, Cellpose runs in an isolated Python subprocess environment (per spec / constitution). There are two viable ways to invoke it inside that subprocess:

- **CLI invocation**: `cellpose ...` with flags as documented in the Cellpose CLI.
- **Python API invocation**: `cellpose.models.CellposeModel(...).eval(...)`.

Findings from Cellpose docs:

- CLI defaults to saving a `*_seg.npy` "bundle" (unless `--no_npy`), and can optionally save masks as PNG/TIF, flows/outlines previews, and ImageJ ROI zips.
- The `_seg.npy` file is explicitly described as the "load in GUI" format, with fields like `masks`, `outlines`, `flows` (including raw `[dY, dX, cellprob]` or `[dZ, dY, dX, cellprob]`), etc.
- In Cellpose 4 / Cellpose-SAM:
  - `models.Cellpose` is removed; `models.CellposeModel` is the supported API.
  - "Channels" are no longer an input in the same way for Cellpose-SAM (it uses the first 3 channels and is trained to be channel-order invariant). CLI flags `--chan/--chan2/--invert/--all_channels` are documented as "Deprecated in v4.0.1+, not used."

Tradeoffs (MCP server context):

- CLI pros:
  - Very stable user-facing surface (`--help` and docs cover the flags).
  - Convenient "one command produces a folder of artifacts" behavior.
- CLI cons (important here):
  - The CLI's `--save_tif` output is a TIFF mask, but not necessarily OME-TIFF with preserved axes/physical pixel sizes.
  - Outputs are multi-file and default to writing next to inputs (must carefully manage `--savedir`/naming and allowlists).
  - It is hard to return rich structured outputs (masks/flows/diams) without relying on vendor files.

- API pros:
  - Direct access to `masks, flows, styles, diams` from `CellposeModel.eval(...)`.
  - Enables a controlled output contract: write the required **label image** to OME-TIFF using the project's preferred I/O stack, while also persisting Cellpose's richer "bundle" output for power users / reproducibility.
  - Easier to ensure "write only to artifact store work dir" (no surprise writes).
- API cons:
  - Requires more wrapper code (image I/O, axes handling, saving outputs).

Decision:

- Use the **Python API** (`CellposeModel.eval`) inside the tool subprocess for the actual computation and artifact writing.
- **Do NOT use CLI argparse as the source of truth for parameter schemas** — CLI params diverge from API params, and Cellpose v4 deprecated several CLI flags. See Section 11 for the recommended approach.

## 9) Output format tension: OME-TIFF intermediates vs Cellpose `_seg.npy`

Problem statement:

- Project spec currently states: "The default intermediate artifact format is OME-TIFF".
- Cellpose's canonical rich output is `*_seg.npy` (a NumPy pickled dict), and important non-mask outputs (e.g., raw flows and cellprob) live there.
- If we force *everything* into OME-TIFF, we risk:
  - confusing users who expect Cellpose outputs to look like Cellpose outputs;
  - losing information or structure (flows are a heterogeneous list of arrays + metadata; OME-TIFF is not a natural container for a dict);
  - creating many "mystery files" (multiple OME-TIFFs for each intermediate array).

Findings (from Cellpose Outputs docs):

- `_seg.npy` contains: `filename`, `masks`, `outlines`, `chan_choose`, `ismanual`, `flows` (including raw `[dY, dX, cellprob]` / `[dZ, dY, dX, cellprob]`), and `zdraw`.
- The docs explicitly note: "the 'img' is no longer saved in the `*_seg.npy` file to save time."

Recommendation (dual-output strategy):

- Keep **OME-TIFF** as the default for *image-like* artifacts that are meant to be consumed by downstream workflow steps:
  - `LabelImageRef` → instance label image as OME-TIFF.
- Also emit **tool-native artifacts** when users may benefit from "full-fidelity" output:
  - `NativeOutputRef` → the tool's native output bundle (e.g., Cellpose `*_seg.npy`, StarDist `*_results.npz`, etc.). This is a **tool-agnostic reference type**; the actual format varies by tool and is recorded in `ArtifactRef.format`.
  - Optional additional vendor/preview outputs (all should be opt-in):
    - ImageJ ROI archive (`*_rois.zip`) via `--save_rois` / `io.save_rois`.
    - PNG/TIF previews via `io.save_masks(..., png=True/tif=True, save_flows=True, save_outlines=True)`.

This resolves both goals:

- Workflow interoperability (OME-TIFF label is clean and standard).
- Reproducibility and Cellpose-native UX (the `_seg.npy` bundle preserves flows + metadata and is loadable in the Cellpose GUI).

## 10) Pivot: "vendor formats" for non-image artifacts

Decision to propose:

- Clarify the "OME-TIFF pivot" as: **OME-TIFF is the default for image artifacts**, not a universal container for all intermediate data.

Rationale:

- Some artifacts are intrinsically non-image or structured (e.g., `_seg.npy` dict, logs, workflow records). Forcing them into OME-TIFF either discards information or creates unnatural encodings.

Practical recommendation for v0.1 artifact typing:

- Continue to use `ArtifactRef.type` to describe *semantic role* (e.g., `LabelImageRef`, `LogRef`, `NativeOutputRef`).
- Use `ArtifactRef.format` to describe *on-disk format*:
  - `OME-TIFF` for label images.
  - `cellpose-seg-npy` for Cellpose `*_seg.npy`.
  - `stardist-results-npz`, `imagej-roi-zip`, etc. for other tools.

**Note on extensibility**: The set of `ArtifactRef.format` values is **open and tool-dependent**. Each tool pack declares the formats it produces in its manifest or `meta.describe` output. The core server does not hardcode format handling; instead, format-specific logic (if any) is resolved dynamically at runtime based on the format string. This ensures new tools can introduce new native formats without requiring core changes.

## 11) Dynamic parameter schema extraction via `meta.describe` protocol

### Problem statement

The original recommendation to derive parameter schemas from Cellpose's CLI argparse is problematic:

1. **CLI params ≠ API params** — The CLI has different parameters than `CellposeModel.eval()`, and the mapping is not 1:1.
2. **Deprecated CLI flags** — Cellpose v4 deprecated channel selection flags (`--chan`, `--chan2`, etc.) that the API doesn't use.
3. **Scalability** — Manually maintaining JSON Schema for each tool version is high-maintenance and error-prone.

### Decision: Hybrid `meta.describe` protocol

Implement a **runtime introspection protocol** where tool packs expose a `meta.describe` function that returns JSON Schema for their parameters. This combines automatic introspection (names, types, defaults) with curated descriptions.

Key design principles:

1. **Introspect for structure** — Use `inspect.signature()` for Python APIs or argparse introspection for Python CLIs to get parameter names, types, and defaults automatically.
2. **Curate for semantics** — Maintain a descriptions dictionary for important parameters; unknown params get a fallback description.
3. **Graceful degradation** — Missing descriptions don't break functionality; new params appear automatically when tools update.

### Introspection strategies by tool type

| Tool Type | Introspection Method | Example |
|-----------|---------------------|---------|
| Python API | `inspect.signature(func)` | Cellpose, StarDist, scikit-image |
| Python CLI (argparse) | `parser._actions` iteration | CellProfiler, many Python tools |
| Structured CLI help | Parse `--help-json` output | Modern CLIs with machine-readable help |
| Legacy binary | Manual schema (fallback) | ImageJ headless, compiled tools |

### Benefits

| Aspect | Manual Schema (rejected) | `meta.describe` Protocol |
|--------|--------------------------|--------------------------|
| New param added | Manual update required | Auto-discovered |
| Default changed | Manual update required | Auto-reflected |
| Param removed | Manual update required | Auto-removed |
| User upgrades tool | Must wait for manifest update | Works immediately |
| Maintenance burden | High | Low (descriptions only) |

### Implementation

See `specs/001-cellpose-pipeline/meta-describe-protocol.md` for the full protocol specification and implementation sketch.

### Notes for correctness / future-proofing

- Cellpose 4 deprecates several CLI "channel selection" flags; the tool schema should reflect that (handled automatically by introspecting the API, not CLI).
- For usability, the MCP tool should likely expose "channel selection" in terms of OME axes/indices (what the user has), rather than in legacy Cellpose channel codes.

### Actionable follow-up

- Update `specs/001-cellpose-pipeline/tasks.md` implementation notes to use `cellpose.models.CellposeModel` (not `models.Cellpose`, which Cellpose docs state is removed in v4).
- Implement `meta.describe` protocol in core and Cellpose tool pack.
