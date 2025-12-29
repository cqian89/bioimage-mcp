# Implementation Plan: 010-image-artifact (Bioio-based)

This plan implements standardized image artifact handling using `bioio` across current tool environments. It relies on artifact references and manifest `Port.format` hints to orchestrate cross-environment compatibility.

## Constitution Gate
- **I. Stable MCP Surface**: Keep responses compact; discovery remains paginated/summarized; no embedding large arrays.
- **II. Isolated Tool Execution**: Readers/writers (including proprietary ingest) live in tool envs (primarily `bioimage-mcp-base`), not the core server env.
- **III. Artifact References Only**: All inter-tool I/O is by artifact reference (URI + metadata), never raw image payloads.
- **IV. Reproducibility & Provenance**: Environment changes update lockfiles; conversion runs are recorded with inputs/outputs.
- **V. Safety, Testing, Observability**: Permission decisions and conversions are logged; changes include automated tests.
- **VI. Test-Driven Development**: Tests are written and failing before implementation tasks for each phase/story.

## Conversion Boundary
- **Core orchestrates**: Determines whether an input artifact matches the target tool’s expected format (via artifact metadata and manifest `Port.format`).
- **Base executes**: If conversion is required, core invokes a conversion function in the `base` tool environment and uses the returned artifact reference.

## Phase 1: Environment & Fixtures (Foundation)
- Select/add a small, redistributable CZI fixture for integration tests.
- Update `envs/bioimage-mcp-base.yaml` to include `bioio` + plugins needed for OME-TIFF, OME-Zarr conversion, and CZI ingest.
- Update `envs/bioimage-mcp-cellpose.yaml` to include `bioio` + `bioio-ome-tiff`.
- Regenerate lockfiles with `conda-lock`.
- Verify health via `python -m bioimage_mcp doctor`.

## Phase 2: Manifest / Schema Alignment
- Add stricter validation / normalization of `Port.format` values in `src/bioimage_mcp/registry/manifest_schema.py` (canonical `OME-TIFF` / `OME-Zarr`).
- Update tool manifests (`tools/base/manifest.yaml`, `tools/cellpose/manifest.yaml`) to use canonical `Port.format` spelling.
- Add migration notes covering manifest/schema semantics.

## Phase 3: Tool Code Standardization
- **Base tools**: Update I/O helpers to use `BioImage` for reading and standard writers for output.
- **Cellpose**: Replace direct image I/O with `BioImage(path).data`; handle 5D normalization.

## Phase 4: Core Orchestration
- Implement format compatibility checks that select conversion steps when needed (via base conversion functions).

## Phase 5: Artifact Metadata Enrichment
- Populate `ArtifactRef.metadata` with shape/axes, dtype, pixel sizes, and channel names extracted via `bioio` `StandardMetadata`.
- Ensure metadata is visible via `describe_artifact` and preserved across at least one write step.

## Phase 6: Documentation & Migration
- Update tutorials and developer docs to reflect the standard `BioImage` pattern.
- Add explicit migration notes for tool authors (manifest format hints, expected axes, metadata invariants).

## Testing Strategy
- **Contract**: Env dependency contracts + manifest/format contracts.
- **Unit**: BioImage 5D normalization + metadata extraction.
- **Integration**: CZI -> OME-TIFF ingest; phasor workflow from converted OME-TIFF; metadata preservation round-trip.

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Proprietary readers increase dependency footprint | Keep proprietary readers only in `base` env; do not add to core or minimal tool envs |
| Large data conversion memory pressure | Use bioio/dask backed reads; write chunked formats where applicable |
| Format string drift across manifests | Enforce canonical values via contract tests and schema validation |
