# Implementation Plan: Phasor Workflow Usability Fixes

**Branch**: `006-phasor-usability-fixes` | **Date**: 2025-12-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-phasor-usability-fixes/spec.md`

## Summary

Fix critical usability issues blocking phasor-FLIM workflows:
1. **Discovery infrastructure** - Resolve ServerSession.id AttributeError preventing tool discovery
2. **Schema introspection** - Fix empty params_schema from describe_function
3. **Phasor calibration** - Add calibration functionality for quantitative FLIM analysis
4. **IO compatibility** - Add bioio-bioformats for better OME-TIFF compatibility

## Technical Context

**Language/Version**: Python 3.13 (core server); Python 3.13 (base tool env)
**Primary Dependencies**: MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `phasorpy`, `bioio-bioformats`
**Storage**: Local filesystem artifact store + SQLite index
**Testing**: `pytest` with TDD workflow (red-green-refactor)
**Target Platform**: Linux-first (macOS/Windows best-effort)
**Project Type**: Python service + CLI
**Performance Goals**: Bounded MCP payload sizes; paginated discovery responses
**Constraints**: No large binary payloads in MCP; artifact references only
**Scale/Scope**: Tool catalog growth supported via pagination and filtering

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Stable MCP surface**: Discovery fixes maintain existing API contracts; no new endpoints added. All discovery responses remain paginated.
- [x] **Summary-first responses**: Full schemas still fetched on-demand via describe_function; manifest params_schema remains minimal.
- [x] **Tool execution isolated**: Calibration added to `base` tool pack (isolated env); bioio-bioformats added to base env only.
- [x] **Artifact references only**: Phasor coordinates stored as 2-channel BioImageRef; no binary data in MCP messages.
- [x] **Reproducibility**: Calibration records reference lifetime, frequency, harmonic in provenance; lockfiles updated.
- [x] **Safety + debuggability**: All fixes require unit tests and contract tests (TDD); helpful error messages for discovery failures.

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/006-phasor-usability-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output - completed
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.yaml         # API contract changes
├── checklists/
│   └── review.md        # Code review checklist
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── api/
│   ├── server.py        # FIX: ServerSession.id -> get_session_identifier()
│   └── discovery.py     # FIX: schema enrichment debugging
├── sessions/
│   └── manager.py       # Session management (unchanged)
└── registry/
    └── schema_cache.py  # Schema caching (unchanged)

tools/base/
├── bioimage_mcp_base/
│   ├── transforms.py    # ADD: phasor_calibrate function
│   ├── io.py            # ADD: load_image_fallback() with reader chain
│   │                    # UPDATE: existing load_image() to use fallback internally
│   └── entrypoint.py    # FIX: meta.describe schema extraction
└── manifest.yaml        # ADD: base.phasor_calibrate function entry

envs/
└── bioimage-mcp-base.yaml  # ADD: openjdk, scyjava, bioio-bioformats

tests/
├── contract/
│   ├── test_discovery_contract.py  # ADD: session identifier tests
│   └── test_phasor_calibrate.py    # NEW: calibration contract tests
├── integration/
│   └── test_io_fallback.py         # NEW: reader fallback chain tests
└── unit/
    └── api/
        └── test_server_session.py  # NEW: session helper tests
```

**Structure Decision**: Single project layout with isolated tool environments. Core server fixes in `src/bioimage_mcp/api/`, tool functionality in `tools/base/`.

**Note on io.py**: The base toolkit already has an `io.py` with `load_image()` function. This feature adds `load_image_fallback()` as the new implementation with ordered reader chain, then updates `load_image()` to delegate to it for backward compatibility.

## Complexity Tracking

> No constitution violations requiring justification. All changes follow established patterns.

| Area | Approach | Constitution Alignment |
|------|----------|----------------------|
| Session ID | Memory-based fallback | Stable MCP surface maintained |
| Schema enrichment | Fix meta.describe | On-demand introspection preserved |
| Calibration | New function in base | Isolated tool execution |
| IO fallback | Explicit reader chain | Artifact references maintained |

## Implementation Phases

### Phase 1: Discovery & Schema Fixes (P1 - Critical)
- Fix ServerSession.id AttributeError
- Fix describe_function returning empty schema
- Add contract tests for discovery endpoints

### Phase 2: Phasor Calibration (P2 - High)
- Implement base.phasor_calibrate
- Update manifest.yaml
- Add unit and contract tests

### Phase 3: IO Compatibility (P2 - Medium)
- Add bioio-bioformats to environment
- Implement load_image_fallback()
- Add integration tests

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| MCP SDK API changes | Pin version; monitor releases |
| Java/JVM issues on some platforms | Document platform-specific setup; tifffile fallback |
| Calibration math errors | Use phasorpy implementation; verify with known data |
| Schema cache inconsistency | Add cache invalidation on version change |
