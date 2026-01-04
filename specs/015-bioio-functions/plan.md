# Implementation Plan: Bioimage I/O Functions

**Branch**: `015-bioio-functions` | **Date**: 2026-01-04 | **Spec**: `specs/015-bioio-functions/spec.md`
**Input**: Feature specification from `/specs/015-bioio-functions/spec.md`

## Summary

Provide 6 curated bioimage I/O functions under the `base.io.bioimage.*` namespace for AI agents to perform common image I/O tasks: **load**, **inspect**, **slice**, **validate**, **get_supported_formats**, and **export**. This consolidates I/O operations and replaces the deprecated `base.bioio.export` function.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic>=2.0`, `bioio`, `bioio-ome-tiff`, `bioio-ome-zarr`, `bioio-imageio` (PNG/JPG via imageio plugin). CSV export should use the Python standard library (no `pandas`).  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest` with contract/unit/integration layers  
**Target Platform**: Linux-first (macOS/Windows best-effort)  
**Project Type**: Python service + CLI  
**Performance Goals**: Bounded MCP payload sizes; fast env installs via micromamba  
**Constraints**: No large binary payloads in MCP; artifact references only  
**Scale/Scope**: Tool catalog can grow; discovery must remain paginated

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: No new MCP endpoints. 6 new functions added via existing registry; `base.bioio.export` removed.
- [x] Version bump justification: Bump `tools/base/manifest.yaml` `tool_version` (currently `0.1.0`) to the next MINOR version to reflect adding 6 functions and removing the deprecated export function.
- [x] Summary-first responses: All functions return artifact refs (BioImageRef, TableRef) or concise JSON metadata - no large payloads.
- [x] Tool execution isolated: All functions run in `bioimage-mcp-base` environment; no new env requirements.
- [x] Artifact references only: Inputs/outputs use BioImageRef, TableRef. No binary data in MCP messages.
- [x] Reproducibility: Function calls record input refs, parameters, output refs. Standard workflow replay applies.
- [x] Safety + debuggability: Path validation against `filesystem.allowed_read/allowed_write`; structured error responses; provenance logging; TDD tests required.

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/015-bioio-functions/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API schemas)
│   └── io-functions.yaml
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
tools/base/
├── manifest.yaml                   # Function definitions - ADD 6 new, REMOVE base.bioio.export
└── bioimage_mcp_base/
    ├── entrypoint.py               # Request dispatch - UPDATE routing
    ├── utils.py                    # BioImage loading utilities (existing)
    └── ops/
        ├── export.py               # REMOVE - replaced by base.io.bioimage.export
        ├── io.py                   # NEW - All 6 base.io.bioimage.* functions
        └── __init__.py

tests/
├── contract/
│   └── test_io_functions_schema.py    # NEW - Schema validation for 6 functions
├── integration/
│   └── test_io_workflow.py            # NEW - Load→slice→export workflow tests
└── unit/
    └── api/
        └── test_io_functions.py       # NEW - Unit tests for each function
```

**Structure Decision**: Single Python package structure. Implementation in `tools/base/bioimage_mcp_base/ops/io.py` with corresponding manifest entries. All functions are part of the existing base toolkit - no new tool packs required.

**Native dimensions policy**: Preserve native axes by default (prefer `img.reader.data`/`img.reader.xarray_data` over `img.data`), and only normalize/expand to 5D when the output format requires it (e.g., some OME-TIFF exports) or an explicit dimension requirement exists.

## Complexity Tracking

| Area | Complexity | Notes |
|------|------------|-------|
| Slicing Logic | Medium | Map dimension labels to xarray/numpy indexing while preserving metadata |
| Path Validation | Low | Leverage existing filesystem allowlist infrastructure |
| Format Support Query | Low | Query bioio entrypoints |
| Metadata Extraction | Low | Use bioio.BioImage properties |
| Export Migration | Low | Logic already exists in export.py, just reorganizing |

**No Constitution Violations**: All gates pass. No violations requiring justification.
