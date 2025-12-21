# Implementation Plan: FLIM Phasor Analysis Gap Fix

**Branch**: `003-base-tool-schema` | **Date**: 2025-12-21 | **Spec**: [specs/003-base-tool-schema/spec.md](spec.md)
**Input**: Feature specification from `specs/003-base-tool-schema/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.codex/prompts/speckit.plan.md` for the execution workflow.

## Summary

Implement phasor analysis capabilities in the base toolset, enabling FLIM workflows. This includes a phasor transform tool (using `phasorpy` likely), an intensity image derivation tool, and an optional denoising tool (using `scikit-image`). The implementation must handle OME-TIFF artifacts, support multi-channel inputs, and include an end-to-end validation workflow integrating with the existing segmentation capability.

## Technical Context

**Language/Version**: Python 3.13 (bioimage-mcp-base env)
**Primary Dependencies**: 
- `mcp` (Python SDK)
- `bioio`, `bioio-ome-tiff` (I/O)
- `phasorpy` (Phasor transform logic - NEEDS VERIFICATION of capabilities)
- `scikit-image` (Denoising)
- `numpy` (Array manipulation)
- `pydantic` (Schemas)
**Storage**: Local filesystem artifact store + SQLite index
**Testing**: `pytest`, with `tests/integration/` for the E2E workflow.
**Target Platform**: Local/on-prem; Linux-first.
**Project Type**: Python MCP Server Tools
**Constraints**: 
- Artifact references only for I/O.
- Input/Output must be OME-TIFF.
- No OME-Zarr support for this feature (fail fast).
- Memory management for large datasets (warn >4GB).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: New tools added (`phasor_transform`, `denoise_image`, `derive_intensity`) as separate functions; no breaking changes to discovery.
- [x] Summary-first responses: Tools will be discoverable via paginated list; full schemas on demand.
- [x] Tool execution isolated: Phasor tools run in `bioimage-mcp-base` env; segmentation runs in `bioimage-mcp-cellpose`.
- [x] Artifact references only: All inputs/outputs are `BioImageRef` (OME-TIFF).
- [x] Reproducibility: Workflow run records will capture parameters (e.g., bin mapping mode, filter params) and tool versions.
- [x] Safety + debuggability: Inputs validated (dims, format); standard logging; unit and integration tests planned.

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
├── transforms.py        # Phasor transform logic
├── preprocess.py        # Denoising logic
├── io.py                # Artifact I/O helpers (existing)
└── descriptions.py      # Tool descriptions

tests/
├── unit/
│   └── base/
│       ├── test_phasor.py     # Unit tests for phasor transform
│       └── test_denoise.py    # Unit tests for denoising
└── integration/
    └── test_flim_phasor_e2e.py # End-to-end workflow validation
```

**Structure Decision**: Extend existing `tools/base/bioimage_mcp_base` package.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
