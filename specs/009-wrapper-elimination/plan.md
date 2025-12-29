# Implementation Plan: Wrapper Elimination & Enhanced Dynamic Discovery

**Branch**: `009-wrapper-elimination` | **Date**: 2025-12-29 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/009-wrapper-elimination/spec.md`

## Summary

Remove 15 thin wrapper functions from the static manifest and enable full dynamic discovery via existing adapters (skimage, scipy, phasorpy). Retain 10 essential wrappers renamed to `base.wrapper.*` namespace, and 6 edge-case wrappers (`flip`, `pad`, `project_sum/max`, `crop`, `normalize_intensity`). Add manifest overlay system for enriching dynamically discovered functions.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic>=2.0`, `bioio`, `scikit-image`, `scipy`, `phasorpy`  
**Storage**: Local filesystem artifact store + SQLite index  
**Testing**: `pytest` with unit, contract, and integration test categories  
**Target Platform**: Cross-platform (Linux, macOS, Windows)  
**Project Type**: Python service + CLI with subprocess-based tool execution  
**Performance Goals**: List/Search < 200ms (cold); Describe < 100ms (warm)  
**Constraints**: All I/O via artifact references; tool isolation in conda envs  

### Key Technical Decisions

1. **Overlay merging location**: Perform in `loader.py` during manifest registration (merging discovered functions with manifest + overlays)
2. **Legacy redirect mechanism**: Handled in entrypoint.py FN_MAP with LEGACY_REDIRECTS dict
3. **Wrapper namespace**: `base.wrapper.<category>.<function>` for essential wrappers
4. **Dynamic naming**: `base.<library>.<module>.<function>` (e.g., `base.skimage.filters.gaussian`)

## Constitution Check

*GATE: Passes all checks.*

- [x] **Stable MCP surface**: No new endpoints. Function IDs change (internal), paginated discovery unchanged.
- [x] **Summary-first responses**: `describe_function()` fetches full schema on-demand, including merged overlays.
- [x] **Tool execution isolated**: All functions run in `bioimage-mcp-base` env via subprocess.
- [x] **Artifact references only**: Adapters handle array ↔ artifact conversion; no change to I/O model.
- [x] **Reproducibility**: Legacy redirects enable replay of old workflows; new recordings use new IDs.
- [x] **Safety + debuggability**: Deprecation warnings logged; overlay validation errors logged; tests for overlay merging.

## Project Structure

### Documentation (this feature)

```text
specs/009-wrapper-elimination/
├── plan.md              # This file
├── research.md          # Technical research findings
├── data-model.md        # Entity definitions
├── quickstart.md        # Validation steps
├── contracts/           # API contract definitions
│   └── manifest-overlay.yaml
├── checklists/
│   └── impl-checklist.md
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
src/bioimage_mcp/api/
├── discovery.py         # Uses merged manifests from loader

src/bioimage_mcp/registry/
├── manifest_schema.py   # Add FunctionOverlay model
├── loader.py            # Overlay lookup, merge, and validation logic

tools/base/
├── manifest.yaml        # Update with overlays, remove thin wrappers
├── bioimage_mcp_base/
├── entrypoint.py    # Update FN_MAP, add LEGACY_REDIRECTS
├── preprocess.py    # Remove thin wrappers, keep denoise_image
├── transforms.py    # Remove thin wrappers, keep phasor funcs
└── wrapper/         # NEW: organized wrapper package
    ├── __init__.py
    ├── io.py
    ├── axis.py
    ├── phasor.py
    ├── denoise.py
    └── edge_cases.py

tests/
├── contract/
│   └── test_overlay_schema.py    # NEW
├── unit/registry/
│   └── test_overlay_merge.py     # NEW
└── integration/
    └── test_dynamic_execution.py # Update function names
```

**Structure Decision**: Single project structure; changes span registry (core) and tools/base (tool pack).

## Complexity Tracking

No constitution violations. Feature simplifies the codebase:
- Reduces static function count from 31 to 16
- Eliminates duplicated I/O boilerplate
- Enables consistent naming via dynamic discovery
