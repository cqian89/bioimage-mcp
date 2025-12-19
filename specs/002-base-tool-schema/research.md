# Research: Base Tool Schema Expansion

**Date**: 2025-12-19
**Status**: Complete

This research resolves the open technical questions needed to design the base-tool schema expansion and live workflow validation.

## 1. Tool Pack Strategy (Base Toolkit Placement)

**Decision**: Add a dedicated base image-processing tool pack (proposed `tools/base/` with `tool_id: tools.base`) that runs in `env_id: bioimage-mcp-base`. Keep `tools/builtin` for small “system utilities” (e.g., format conversion) and backward compatibility.

**Rationale**:
- Separates “platform utilities” from the fast-growing base image-processing surface (≥20 functions).
- Keeps the MCP discovery surface organized for users (search results are less noisy).
- Maintains Constitution Principle I (stable MCP surface) by being additive: existing `tools.builtin.*` functions remain valid.

**Alternatives Considered**:
- Extend `tools/builtin` with all base functions: simplest mechanically, but mixes concerns and makes the “built-ins” tool pack large and harder to curate.
- Create multiple base packs (I/O vs transforms vs preprocessing): not needed initially; adds fragmentation.

## 2. On-Demand Schema Enrichment (`describe_function` → `meta.describe`)

**Decision**: Wire server-side `describe_function(fn_id)` to call tool-side `meta.describe` on cache miss (or stale entry) and return the enriched schema.

**Rationale**:
- Matches FR-001/FR-002/FR-003 and Constitution Principle I: discovery remains summary-first, while schemas are fetched only when explicitly requested.
- Ensures enrichment executes in the owning tool environment (Principle II).
- Tool packs already implement `meta.describe` handlers and shared introspection utilities exist.

**Alternatives Considered**:
- Eager enrichment at startup: violates “summary-first” spirit (wastes work and risks slow startup), and increases failure surface.
- Store full schemas in manifests: high maintenance burden and drift risk.

## 3. Schema Introspection Source and Documentation Quality

**Decision**: Use `src/bioimage_mcp/runtimes/introspect.py::introspect_python_api` for schema structure (types/defaults/required) plus curated per-parameter description maps maintained in the tool pack.

**Rationale**:
- Automatic extraction reduces duplication and stays aligned with function signatures.
- Curated descriptions prevent “See docs” ambiguity and make tool calling reliable for LLMs.

**Alternatives Considered**:
- Docstring parsing for descriptions: brittle and inconsistent across libraries.
- Fully manual JSON Schema authoring per function: too costly for ≥20 functions.

## 4. Schema Cache Persistence

**Decision**: Persist enriched schemas in a **local JSON file** keyed by `tool_id + tool_version + fn_id` and invalidate on tool version change.

**Proposed location**: `${artifact_store_root}/state/schema_cache.json`.

**Rationale**:
- Satisfies the explicit clarification: “Local JSON file”.
- Keeps cache colocated with other local state (`artifact_store_root/state/…`) and within configured filesystem allowlists.
- Simple to inspect, diff, and purge.

**Alternatives Considered**:
- SQLite-only cache: already present in the repo, but does not satisfy the “local JSON file” requirement as written.
- In-memory cache only: fails persistence requirement.

## 5. Curated Base Function Set (≥20)

**Decision**: Curate an initial base function catalog spanning I/O, transforms, and pre-processing. Functions operate on `BioImageRef` inputs and produce `BioImageRef` outputs (default intermediate format: OME-Zarr).

**Rationale**:
- Enables meaningful workflows without pulling specialized packs.
- Matches FR-005/FR-006/SC-001.

**Alternatives Considered**:
- Only expose a handful of “demo” functions: does not meet SC-001.

### Proposed initial catalog (v0)

**Image I/O / Format**
- `base.convert_to_ome_zarr` (already exists as `builtin.convert_to_ome_zarr`; duplicated under `tools.base` for consistency)
- `base.export_ome_tiff`

**Transforms**
- `base.resize`
- `base.rescale`
- `base.rotate`
- `base.flip`
- `base.crop`
- `base.pad`

**Pre-processing**
- `base.normalize_intensity` (e.g., percentile-based)
- `base.gaussian`
- `base.median`
- `base.bilateral`
- `base.denoise_nl_means`
- `base.unsharp_mask`
- `base.equalize_adapthist`
- `base.sobel`
- `base.threshold_otsu`
- `base.threshold_yen`
- `base.morph_opening`
- `base.morph_closing`
- `base.remove_small_objects`

**Axis/Dim handling (for microscopy stacks)**
- `base.project_sum` (reduce Z/T bins to intensity)
- `base.project_max`

This list is intentionally focused on common, well-documented primitives with stable semantics and minimal ambiguity.

## 6. Live End-to-End Workflow Validation Design

**Decision**: Add at least one truly “live” integration test that:
- reads a real TIFF from `datasets/FLUTE_FLIM_data_tif`
- executes real tool subprocesses (no monkeypatching `execute_step`)
- produces at least one label/mask artifact (cellpose) when prerequisites exist
- otherwise **skips** with an actionable reason (SC-004)

**Rationale**:
- Contract and unit tests can pass even if subprocess JSON protocol, env isolation, or real image I/O is broken.
- The dataset contains a representative microscopy stack; e.g. `hMSC-ZOOM.tif` has shape `(56, 256, 256)` and can be reduced to a 2D intensity image via `project_sum` before segmentation.

**Alternatives Considered**:
- Mocked integration tests: insufficient; they do not validate real execution.
- Synthetic-only fixtures: useful for speed and licensing, but do not satisfy FR-012 (“use existing datasets/FLUTE_FLIM_data_tif for now”).

## 8. Verified Tool Implementations

Research into `scikit-image`, `bioio`, and `numpy` confirms the following implementation mappings for the base function catalog.

### Image I/O
- `base.export_ome_tiff`: Use `bioio.writers.OmeTiffWriter.save` (requires `bioio-ome-tiff`).
- `base.convert_to_ome_zarr`: Use `bioio.writers.OMEZarrWriter.save` or `ome_zarr.writer.write_image`.

### Transforms
- `base.resize`: `skimage.transform.resize`. Handles nD; use `anti_aliasing=True`.
- `base.rescale`: `skimage.transform.rescale`.
- `base.rotate`: `skimage.transform.rotate`. **Note**: Primarily 2D; for 3D stacks, apply per-slice or use `scipy.ndimage.rotate`.
- `base.flip`: `numpy.flip`.
- `base.crop`: `skimage.util.crop` or standard array slicing.
- `base.pad`: `numpy.pad`.

### Projections
- `base.project_sum`: `numpy.sum` (specify axis, e.g., Z).
- `base.project_max`: `numpy.max`.

### Filters & Restoration
- `base.gaussian`: `skimage.filters.gaussian`. Supports `channel_axis`.
- `base.median`: `skimage.filters.median`. Requires `footprint` for nD.
- `base.bilateral`: `skimage.restoration.denoise_bilateral`.
- `base.sobel`: `skimage.filters.sobel`.
- `base.denoise_nl_means`: `skimage.restoration.denoise_nl_means`.
- `base.unsharp_mask`: `skimage.filters.unsharp_mask`.
- `base.equalize_adapthist`: `skimage.exposure.equalize_adapthist` (CLAHE).

### Segmentation/Morphology
- `base.threshold_otsu`: `skimage.filters.threshold_otsu`.
- `base.threshold_yen`: `skimage.filters.threshold_yen`.
- `base.morph_opening`: `skimage.morphology.opening`. Use `disk` (2D) or `ball` (3D).
- `base.morph_closing`: `skimage.morphology.closing`.
- `base.remove_small_objects`: `skimage.morphology.remove_small_objects`.

### Implementation Notes
- **Data Types**: `skimage` often converts to float64 [0, 1]. Output handling must ensure consistent types for downstream tools (e.g., converting back to uint8/uint16 if required, or updating metadata).
- **nD Handling**: Explicitly handle `channel_axis` where applicable to avoid blurring across channels.
