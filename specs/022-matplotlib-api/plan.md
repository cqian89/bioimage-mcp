# Implementation Plan: Matplotlib API Integration

**Branch**: `022-matplotlib-api` | **Date**: Mon Jan 12 2026 | **Spec**: [specs/022-matplotlib-api/spec.md](spec.md)
**Input**: Feature specification from `/specs/022-matplotlib-api/spec.md`

## Summary
Integrate Matplotlib API into Bioimage-MCP as a first-class citizen for visualization, plotting, and ROI annotation with headless rendering support. Following TDD principles, implement a MatplotlibAdapter (discovery + safe dispatch) and base-tool execution shims, plus FigureRef/AxesRef/AxesImageRef artifact types for stateful figure construction across multiple tool calls.

## Technical Context
- **Language/Version**: Python 3.13 (core server); Python 3.13 (base tool env)
- **Primary Dependencies**: MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `matplotlib>=3.8`, `bioio`, `numpy`
- **Storage**: Local filesystem artifact store + SQLite index (MVP)
- **Testing**: `pytest`, `pytest-asyncio` (TDD - tests first)
- **Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)
- **Project Type**: Python service + CLI
- **Performance Goals**: Bounded MCP payload sizes; auto-cleanup of Figure objects after savefig
- **Constraints**: No large binary payloads in MCP; headless Agg backend only; interactive methods blocked
- **Scale/Scope**: 200+ matplotlib functions exposed via dynamic adapter

## Constitution Check
All 6 principles must be checked:

1. [x] **Stable MCP surface**: No changes to the constitution-defined 8-tool MCP surface; plotting functions are exposed under `base.matplotlib.*` and executed via `run` (discovered via `list`/`describe`).

2. [x] **Summary-first responses**: Function discovery via paginated `list`; full schemas via `describe(id)`.

3. [x] **Tool execution isolated**: Matplotlib runs in `bioimage-mcp-base` conda environment. No heavy deps added to core server.

4. [x] **Artifact references only**: Uses FigureRef, AxesRef, AxesImageRef (memory-backed ObjectRef subclasses) and PlotRef (file-backed). No raw arrays in MCP messages.

5. [x] **Reproducibility**: Workflow logs capture every plotting step, parameters, and artifact references. Sessions can be replayed.

6. [x] **Safety + debuggability**: Headless Agg backend enforced; interactive methods blocked via denylist; auto-cleanup prevents memory leaks; all changes require tests.

## Project Structure

### Documentation (this feature)
```text
specs/022-matplotlib-api/
├── spec.md               # Feature specification
├── plan.md               # This file
├── research.md           # Phase 0 research findings
├── data-model.md         # Entity definitions
├── quickstart.md         # Usage examples
├── contracts/            # API schemas
│   ├── matplotlib-functions.json
│   └── artifact-refs.json
└── tasks.md              # Phase 2 output (NOT created by this plan)
```

### Source Code (repository root)
```text
src/bioimage_mcp/
├── artifacts/
│   └── models.py                    # UPDATE: Add FigureRef, AxesRef, AxesImageRef, extend PlotRef
├── registry/
│   └── dynamic/
│       └── adapters/
│           ├── matplotlib.py        # NEW: MatplotlibAdapter (discovery + safe dispatch)
│           └── matplotlib_allowlists.py # NEW: Allowed/blocked API surface
├── api/
│   └── schemas.py                   # UPDATE: Register new artifact types

tools/base/
├── manifest.yaml                    # UPDATE: Add matplotlib dynamic_source
└── bioimage_mcp_base/
    └── ops/
        └── matplotlib_ops.py        # NEW: Specialized matplotlib operations

envs/
└── bioimage-mcp-base.yaml          # UPDATE: Add matplotlib>=3.8 dependency

tests/
├── contract/
│   ├── test_matplotlib_env.py               # NEW: Env/lockfile dependency checks
│   └── test_matplotlib_adapter_discovery.py # NEW: Discovery + schema contract tests
├── unit/
│   └── registry/
│       └── test_matplotlib_adapter.py # NEW: Adapter unit tests (allowlist/denylist, safety)
└── integration/
    ├── test_us1_histograms.py         # NEW: US1 end-to-end
    ├── test_us2_roi_overlays.py       # NEW: US2 end-to-end
    ├── test_us3_subplots.py           # NEW: US3 end-to-end
    ├── test_us4_scatter_plots.py      # NEW: US4 end-to-end
    ├── test_us5_time_series.py        # NEW: US5 end-to-end
    ├── test_us6_export.py             # NEW: US6 end-to-end
    ├── test_us7_stats_plots.py        # NEW: US7 end-to-end
    ├── test_us8_z_profiles.py         # NEW: US8 end-to-end
    ├── test_matplotlib_axes_features.py  # NEW: Axes styling/annotation/colorbar
    ├── test_matplotlib_session_replay.py # NEW: Session export/replay determinism
    └── test_matplotlib_memory_leak.py    # NEW: Figure leak regression
```

**Structure Decision**: Single project with tools/base extension. No new tool pack needed since matplotlib is a transitive dependency appropriate for base environment.

## Complexity Tracking

No constitution violations requiring justification. The feature:
- Uses existing MCP surface (no new tools)
- Adds specialized ObjectRef subclasses following established patterns (GroupByRef)
- Extends existing base tool pack rather than creating new one

## Implementation Phases

### Phase 1: Environment & Models (TDD)
1. Write failing tests for FigureRef, AxesRef, AxesImageRef models
2. Add matplotlib>=3.8 to envs/bioimage-mcp-base.yaml and update envs/bioimage-mcp-base.lock.yml
3. Implement artifact models in src/bioimage_mcp/artifacts/models.py
4. Register types in API schemas

### Phase 2: Dynamic Adapter (TDD)
1. Write failing tests for MatplotlibAdapter discovery
2. Implement allowlist/denylist in matplotlib_allowlists.py
3. Implement MatplotlibAdapter with Agg backend enforcement
4. Add dynamic_source to base manifest.yaml

### Phase 3: Core Operations (TDD)
1. Write failing tests for subplots, imshow, savefig
2. Implement pyplot factory functions (figure, subplots, close)
3. Implement Figure methods (savefig, tight_layout, suptitle)
4. Implement Axes plotting methods (imshow, plot, scatter, hist)

### Phase 4: Advanced Features (TDD)
1. Write failing tests for patches and colorbar
2. Implement patch constructors (Circle, Rectangle)
3. Implement add_patch and colorbar
4. Implement axes styling methods (set_title, set_xlabel, etc.)

### Phase 5: Integration & Cleanup
1. End-to-end workflow tests
2. Memory leak tests (100+ figure creation)
3. Documentation updates
4. Smoke tests

## Verification Commands

```bash
# Run contract tests (discovery + schemas)
pytest tests/contract/test_matplotlib_adapter_discovery.py -v

# Run unit tests (adapter safety + allowlist/denylist)
pytest tests/unit/registry/test_matplotlib_adapter.py -v

# Run integration tests (requires base env)
conda run -n bioimage-mcp-base pytest tests/integration/test_us*.py -v
conda run -n bioimage-mcp-base pytest tests/integration/test_matplotlib_session_replay.py -v
conda run -n bioimage-mcp-base pytest tests/integration/test_matplotlib_memory_leak.py -v

# Lint check
ruff check src/bioimage_mcp/registry/dynamic/adapters/matplotlib.py tools/base/bioimage_mcp_base/ops/matplotlib_ops.py

# Optional: end-to-end validation
python scripts/validate_pipeline.py
```
