# Implementation Plan: Comprehensive Phasorpy Adapter

**Branch**: `013-phasorpy-adaptor` | **Date**: 2026-01-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-phasorpy-adaptor/spec.md`

## Summary

Expose the full suite of Phasorpy v0.9+ public API functions (75+ functions across 6 modules) to the bioimage-mcp ecosystem through dynamic discovery. This replaces the current hardcoded adapter that only exposes 2 functions with a comprehensive solution that introspects Phasorpy submodules, maps function signatures to standardized I/O patterns, and handles complex outputs including tuples and matplotlib figures.

### Versioning & Migration Notes

- **New Artifact Type**: Introduces `PlotRef` (PNG format) for visualization outputs.
- **Contract Impact**: This is a non-breaking extension to the bioimage-mcp artifact model. Existing tools/clients that do not support `PlotRef` will ignore these outputs.
- **Constitution Alignment**: Satisfies "Stable MCP Surface" by using existing discovery mechanisms and "Artifact References Only" by formalizing visualization storage.

**Key Deliverables**:
- Dynamic function discovery for `phasorpy.phasor`, `phasorpy.lifetime`, `phasorpy.plot`, `phasorpy.filter`, `phasorpy.cursor`, `phasorpy.component`
- New `PlotRef` artifact type for matplotlib figure capture
- Extended IOPattern enum for phasor-specific operations
- End-to-end FLIM workflow: Load → Transform → Calibrate → Plot

## Technical Context

**Language/Version**: Python 3.13 (core server); Python 3.13 (base tool env)  
**Primary Dependencies**: `phasorpy>=0.9.0`, `bioio`, `numpy`, `matplotlib`, `numpydoc`, `mcp>=1.25.0`, `pydantic>=2.0`  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest`, `pytest-asyncio` (contract and integration tests)  
**Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)  
**Project Type**: Python service + CLI with dynamic tool registry  
**Performance Goals**: ≥50 functions discovered; workflow completion <30 seconds  
**Constraints**: No large binary payloads in MCP; artifact references only; phasorpy.io excluded

## Constitution Check

*GATE: Passed after Phase 1 design verification.*

- [x] **Stable MCP surface**: Dynamic discovery via existing `list_tools`/`describe_function` endpoints. No new MCP endpoints required. Functions exposed through pagination.
- [x] **Summary-first responses**: Full schemas fetched on demand via `describe_function(fn_id)`. Discovery returns only summaries.
- [x] **Tool execution isolated**: Phasorpy runs in `bioimage-mcp-base` conda environment via persistent subprocess worker. Heavy deps (matplotlib, numpy C-extensions) stay out of core server.
- [x] **Artifact references only**: All I/O via `BioImageRef` (OME-TIFF). New `PlotRef` type for PNG visualizations. No arrays in MCP messages.
- [x] **Reproducibility**: Parameter schemas and phasorpy version recorded in run logs. Lockfile-pinned environment.
- [x] **Safety + debuggability**: Subprocess crash containment for C-extension errors. Logs persisted as `LogRef`. 
- [x] **Policy Enforcement**: Explicit verification of `allowed_read` allowlist for all vendor format readers.
- [x] **Tests-First (TDD)**: Mandatory failing tests for discovery, artifact creation, and workflows before implementation.

(Reference: `.specify/memory/constitution.md` v0.8.1)

## Project Structure

### Documentation (this feature)

```text
specs/013-phasorpy-adaptor/
├── plan.md              # This file
├── spec.md              # Feature specification
├── proposal.md          # Initial proposal (existing)
├── analysis_report.md   # Phasorpy API audit (existing)
├── research.md          # Phase 0: Research decisions
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Developer guide
├── contracts/
│   └── phasorpy-adapter-contract.md  # API contracts
└── checklists/
    └── implementation-checklist.md   # Phase 2 (not yet created)
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── api/
│   └── schemas.py                    # UPDATE: Add PlotRef type
├── artifacts/
│   ├── models.py                     # UPDATE: Add PlotRef, PlotMetadata
│   └── store.py                      # UPDATE: write_plot() helper
└── registry/
    └── dynamic/
        ├── adapters/
        │   ├── __init__.py           # UPDATE: Ensure phasorpy registered
        │   └── phasorpy.py           # MAJOR UPDATE: Full dynamic discovery
        ├── introspection.py          # UPDATE: Tuple return handling
        └── models.py                 # UPDATE: New IOPattern values

tools/base/
├── manifest.yaml                     # UPDATE: Expand phasorpy modules list
└── bioimage_mcp_base/
    └── dynamic_dispatch.py           # UPDATE: PlotRef handling

tests/
├── contract/
│   └── test_phasorpy_discovery.py    # NEW: Verify 50+ functions
└── integration/
    └── test_phasorpy_workflow.py     # NEW: End-to-end FLIM workflow
```

**Structure Decision**: Single Python project with isolated tool environments. No new tool packs required - phasorpy functions run in existing `bioimage-mcp-base` environment.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New artifact type (PlotRef) | Required for visualization outputs from `plot_phasor` | Returning raw PNG bytes violates artifact reference principle |
| Dynamic introspection | To support 75+ functions without 2000 lines of manual mapping | Manual mapping is unmaintainable and lags library updates |
| Tuple return mapping | Phasorpy core functions return multiple arrays (`(mean, real, imag)`) | Forcing 3 separate function calls is confusing and breaks workflow |
| Matplotlib capture in subprocess | Plots must be captured as artifacts for agent feedback | No visualization is unacceptable for phasor analysis |

## I/O Pattern Categories

| Pattern | Input Type | Output Type | Example Functions |
|---------|------------|-------------|-------------------|
| `SIGNAL_TO_PHASOR` | BioImageRef (Signal) | Multi-BioImageRef (Mean, Real, Imag) | `phasor_from_signal` |
| `PHASOR_TRANSFORM` | Multi-BioImageRef (Real, Imag) | Multi-BioImageRef (Real, Imag) | `phasor_transform`, `phasor_calibrate` |
| `PHASOR_TO_SCALAR` | Multi-BioImageRef | Numeric/Array | `phasor_to_apparent_lifetime` |
| `SCALAR_TO_PHASOR` | Scalars | Multi-BioImageRef | `phasor_from_lifetime` |
| `PLOT` | BioImageRef/Arrays | PlotRef (PNG) | `plot_phasor`, `plot_phasor_image` |
| `GENERIC_ARRAY` | BioImageRef | BioImageRef | `phasor_filter_median` |

## Implementation Phases

### Phase 1: Discovery & Calibrated Workflow (US1 - MVP)
*Goal: Establish dynamic discovery and the core "Load -> Transform -> Calibrate" workflow. No dependency on PlotRef.*
1. Write failing tests for 50+ function discovery and tuple return handling.
2. Update `PhasorPyAdapter` with full module scanning (`phasor`, `lifetime`, `filter`, `cursor`, `component`).
3. Add new IOPattern enum values (excluding PLOT if necessary, but T001 includes it).
4. Implement tuple return mapping and dimension hints for `axis` parameters.
5. Test: `pytest tests/contract/test_phasorpy_discovery.py` and `tests/integration/test_phasorpy_workflow.py` (US1).

### Phase 2: PlotRef & Visualization (US2)
*Goal: Support matplotlib figure capture and the "Plot" workflow step.*
1. Write failing tests for `PlotRef` creation and `plot_phasor` execution.
2. Add `PlotRef` and `PlotMetadata` to artifact models and schemas.
3. Implement matplotlib `Agg` backend capture and `write_plot()` helper.
4. Test: `pytest tests/contract/test_plotref_artifact.py` and `tests/integration/test_phasorpy_workflow.py` (US2).

### Phase 3: Extended Format Support (US3)
*Goal: Normalize vendor-specific formats (PTU, LIF) and preserve metadata.*
1. Verify `bioio-bioformats` and `bioio-lif` plugins in the tool environment.
2. Implement acquisition parameter extraction (`PhasorMetadata`).
3. Test: Integration tests for SDT, PTU, and LIF datasets.

### Phase 4: Polish & Verification
1. Implement error translation and structured logging (`LogRef`).
2. Verify performance: Workflow <30s for 512x512 image.
3. Final documentation updates (tutorials and quickstart).

## Verification Plan

### Automated Tests
- `pytest tests/contract/test_phasorpy_discovery.py`: Verify ≥50 functions discovered (MVP)
- `pytest tests/contract/test_plotref_artifact.py`: Verify PlotRef creation and retrieval
- `pytest tests/integration/test_phasorpy_workflow.py`: End-to-end FLIM analysis (US1, US2, US3)

### Manual Verification
- Use `describe_function("phasorpy.phasor.phasor_from_signal")` via MCP client
- Execute plotting function and verify PNG artifact via `get_artifact`
- Verify `allowed_read` enforcement for vendor files

## Success Criteria (from spec)

- **SC-001**: ≥50 Phasorpy functions registered in MCP tool registry (MVP threshold); 75+ target.
- **SC-002**: Load→Transform→Calibrate→Plot workflow <30 seconds (512x512 image).
- **SC-003**: Zero core server crashes from malformed vendor files (subprocess isolation).
- **SC-004**: 100% of plotted artifacts accessible via `get_artifact` tool.

## Related Documents

- [Feature Spec](./spec.md)
- [Research Decisions](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/phasorpy-adapter-contract.md)
- [Quickstart Guide](./quickstart.md)
- [Phasorpy API Audit](./analysis_report.md)
