# Implementation Plan: FLIM Phasor Analysis Gap Fix

**Branch**: `003-base-tool-schema` | **Date**: 2025-12-21 | **Spec**: [specs/003-base-tool-schema/spec.md](spec.md)
**Input**: Feature specification from `specs/003-base-tool-schema/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.codex/prompts/speckit.plan.md` for the execution workflow.

## Summary

Implement phasor analysis capabilities in the base toolset, enabling FLIM workflows. This includes:

- `base.phasor_from_flim`: converts a FLIM OME-TIFF artifact into phasor coordinate image artifacts (G and S) and a derived integrated intensity image artifact.
- `base.denoise_image`: optional denoising for phasor outputs using `scikit-image` with a structured parameter schema.

The implementation must handle OME-TIFF artifacts, support multi-channel inputs, and include an end-to-end validation workflow integrating with the existing segmentation capability.

## Technical Context

**Language/Version**: Python 3.13 (bioimage-mcp-base env)

**Primary Dependencies**:
- `mcp` (Python SDK)
- `bioio`, `bioio-ome-tiff` (I/O)
- `phasorpy` (Phasor transform logic; validate suitability in tasks T001)
- `scikit-image` (Denoising)
- `numpy` (Array manipulation)
- `pydantic` (Schemas)

**Storage**: Local filesystem artifact store + SQLite index

**Testing**: `pytest`, with `tests/integration/` for the E2E workflow.

**Target Platform**: Local/on-prem; Linux-first.

**Project Type**: Python MCP Server Tools

**Constraints**:
- Artifact references only for I/O.
- Input/Output for this feature is OME-TIFF only; fail fast (with actionable messaging) on OME-Zarr.
- Memory management for large datasets: surface a warning when input exceeds 4GB; proceed unless OOM.

## OME-TIFF Only Rationale (Scoped Exception)

The constitution recommends OME-Zarr as the default for intermediate artifacts, but this feature intentionally constrains I/O to OME-TIFF only:

- The missing capability is specifically for FLIM datasets already represented as OME-TIFF inputs.
- Introducing OME-Zarr support here would expand scope and add dependency/compatibility risk.
- This constraint is scoped to phasor + validation for phase 003 and should not be generalized as a project-wide direction.

## Public Tool Contracts (Deterministic)

These contracts are the basis for unit/integration tests and MUST remain stable once implemented.

- `base.phasor_from_flim`
  - Inputs: FLIM dataset artifact reference (OME-TIFF)
  - Params: includes `time_axis` override (string axis name or integer index, per spec)
  - Outputs: artifact references for `g`, `s`, and `intensity` (integrated intensity), plus a structured `warnings` field when applicable
- `base.denoise_image`
  - Inputs: image artifact reference (OME-TIFF)
  - Params: `filter_type` enum + filter-specific optional params (e.g., `sigma`, `radius`)
  - Outputs: artifact reference for the denoised image, plus `warnings` as needed

## Test Dataset Strategy (Offline-First)

- Use the existing local dataset directory `datasets/FLUTE_FLIM_data_tif/` for integration testing.
- Default selection: `datasets/FLUTE_FLIM_data_tif/Fluorescein_Embryo.tif` (or another stable file in that directory).
- Tests MUST NOT download data by default.
- If the dataset directory is not present (e.g., shallow clone), the E2E test MUST skip with an explicit, actionable reason.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: New tools added (`phasor_from_flim`, `denoise_image`) as separate functions; no breaking changes to discovery.
- [x] Summary-first responses: Tools will be discoverable via paginated list; full schemas on demand.
- [x] Tool execution isolated: Phasor tools run in `bioimage-mcp-base` env; segmentation runs in `bioimage-mcp-cellpose`.
- [x] Artifact references only: All inputs/outputs are artifact references (OME-TIFF).
- [x] Reproducibility: Workflow run records capture resolved params (e.g., time axis, mapping mode, filter params) and tool versions.
- [x] Safety + debuggability: Inputs validated (dims, format); structured logs persisted as artifacts; unit and integration tests planned.

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/003-base-tool-schema/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
tools/base/bioimage_mcp_base/
├── entrypoint.py        # Tool registration + execution wiring
├── transforms.py        # Phasor transform logic
├── preprocess.py        # Denoising logic
├── io.py                # Artifact I/O helpers (existing)
└── descriptions.py      # Tool descriptions

tests/
├── unit/
│   └── base/
│       ├── test_phasor.py              # Unit tests for phasor transform
│       ├── test_phasor_provenance.py   # Unit tests for phasor provenance
│       ├── test_phasor_logging.py      # Unit tests for log artifact persistence
│       └── test_denoise.py             # Unit tests for denoising
└── integration/
    └── test_flim_phasor_e2e.py         # End-to-end workflow validation
```

**Structure Decision**: Extend existing `tools/base/bioimage_mcp_base` package.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
