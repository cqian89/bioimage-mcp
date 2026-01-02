# Implementation Plan: Spec 013: Comprehensive Phasorpy Adapter

**Branch**: `013-phasorpy-adaptor` | **Date**: 2026-01-02 | **Spec**: `specs/013-phasorpy-adaptor/proposal.md`

## Summary

Expose the full suite of [Phasorpy](https://www.phasorpy.org/) (v0.9+) public API functions to the bioimage-mcp ecosystem. This plan replaces the current hardcoded manual adapter with a dynamic discovery system that introspects Phasorpy submodules, maps function signatures to standardized I/O patterns, and handles complex outputs like tuples and matplotlib figures.

## Technical Context

**Language/Version**: Python 3.13 (core server); Python 3.13 (tool env)  
**Primary Dependencies**: `phasorpy>=0.9.0`, `bioio`, `numpy`, `matplotlib`, `numpydoc`  
**Registry**: Dynamic adapter (`src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`)  
**Target Platform**: Local/on-prem  

## Constitution Check

- [x] **Stable MCP Surface**: Functions are exposed via dynamic discovery; tool calls return IDs and artifact references.
- [x] **Summary-first responses**: Discovery uses pagination and summaries; full schemas via `describe_function`.
- [x] **Isolated Tool Execution**: Phasorpy runs in the `bioimage-mcp-base` (or specific `phasorpy`) environment.
- [x] **Artifact References Only**: Large arrays are never embedded; communication via `BioImageRef` and `FileRef`.
- [x] **Reproducibility**: Parameter schemas and environment versions are recorded.
- [x] **Safety**: File access restricted to allowlisted paths.

## Project Structure

### Documentation
```text
specs/013-phasorpy-adaptor/
├── proposal.md          # This file
└── analysis_report.md   # Audit of Phasorpy 0.9 functions and patterns
```

### Source Code
```text
src/bioimage_mcp/
└── registry/
    └── dynamic/
        ├── adapters/
        │   └── phasorpy.py  # MAJOR UPDATE: Dynamic discovery & execution
        └── introspection.py # UPDATE: Enhanced return type & tuple support
```

### Tests
```text
tests/
├── contract/
│   └── test_phasorpy_discovery.py # NEW: Verify all modules are scanned
└── integration/
    └── test_phasorpy_workflow.py  # NEW: End-to-end FLIM analysis workflow
```

## I/O Pattern Mapping Categories

| Pattern | Input Type | Output Type | Example Functions |
|---------|------------|-------------|-------------------|
| `FILE_TO_SIGNAL` | Path/FileRef | BioImageRef (Signal) | `signal_from_sdt`, `signal_from_ptu` |
| `SIGNAL_TO_PHASOR` | BioImageRef (Signal) | Multi-BioImageRef (Mean, Real, Imag) | `phasor_from_signal` |
| `PHASOR_TRANSFORM` | Multi-BioImageRef (Real, Imag) | Multi-BioImageRef (Real, Imag) | `phasor_transform`, `phasor_center` |
| `PHASOR_TO_SCALAR` | Multi-BioImageRef | Numeric/Array | `phasor_to_apparent_lifetime` |
| `PLOT` | BioImageRef/Arrays | ImageRef (PNG) | `plot_phasor`, `plot_phasor_image` |
| `GENERIC_ARRAY` | BioImageRef | BioImageRef | `phasor_filter_median`, `phasor_threshold` |

## Implementation Steps

### Phase 1: Enhanced Discovery & Core Phasor Ops (TDD)
1. **Failing Test**: Create `tests/contract/test_phasorpy_discovery.py` to assert that 50+ functions are discovered across 5+ modules.
2. **Dynamic Scanning**:
   - Update `PhasorPyAdapter.discover` to iterate through `phasorpy.[io, phasor, lifetime, component, filter, cursor]`.
   - Use `inspect.getmembers(module, inspect.isfunction)` and filter for public names.
3. **Refined Introspection**:
   - Update `Introspector` to handle `numpy.ndarray` and `tuple` return hints.
   - Map parameter names (`signal`, `real`, `imag`) to `IOPattern`.
4. **Core Execution**:
   - Update `PhasorPyAdapter.execute` to generically map `BioImageRef` inputs to `numpy` arrays based on parameter name.
   - Handle tuple returns by iterating and saving each array as a separate artifact.

### Phase 2: File I/O & Vendor Readers
1. **Failing Test**: Integration test calling `phasorpy.io.signal_from_sdt` with a sample SDT file.
2. **Path Mapping**:
   - Update `execute` to detect parameters expecting paths (`filename`, `path`).
   - If a `BioImageRef` or `FileRef` is passed to a path parameter, extract the absolute path string.
3. **Multi-Reader Support**:
   - Ensure `phasorpy.io` readers are correctly categorized as `FILE_TO_SIGNAL`.

### Phase 3: Plotting & Visualization
1. **Failing Test**: Call `plot_phasor` and verify a `BioImageRef` (PNG) is returned.
2. **Matplotlib Backend**:
   - In `PhasorPyAdapter.execute`, detect if the result is a `matplotlib.figure.Figure` or `matplotlib.axes.Axes`.
   - Use `fig.savefig()` to capture the output to a temporary PNG file.
   - Return an `ImageRef` artifact.

### Phase 4: Complex Lifetimes & Components
1. **Failing Test**: Call `phasor_to_apparent_lifetime` with frequency scalar and verify correct output.
2. **Scalar Handling**:
   - Ensure `Introspector` correctly maps `int/float` parameters to JSON Schema `integer/number`.
   - Verify `execute` passes these scalars through from `params` to the function.

## Key Technical Decisions

### 1. Dynamic Discovery vs. Hardcoded Manifest
- **Decision**: Use `inspect` and `importlib` for full dynamic discovery.
- **Rationale**: Phasorpy is evolving rapidly (v0.9). Manual updates are error-prone and will lag behind the library.

### 2. Multi-Array Output Handling
- **Decision**: Functions returning tuples will produce multiple artifact outputs.
- **Naming**: Outputs will be named based on the function's return names in docstrings (if parseable) or `output_0`, `output_1`, etc.

### 3. Plotting Strategy
- **Decision**: Capture plots as PNG artifacts.
- **Rationale**: Agents need visual feedback to verify phasor distributions. PNG is the most compatible format for MCP clients.

### 4. Interchange Format
- **Decision**: Default to OME-TIFF for all intermediate array storage.
- **Rationale**: Consistent with Spec 011 and ensures metadata (axes) is preserved.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Matplotlib capture | Required for visualization tools (`plot_phasor`). | Returning raw data is useless for "plotting" functions. |
| Tuple return mapping | Phasorpy core functions (`phasor_from_signal`) return multiple arrays. | Forcing users to call 3 separate functions to get 3 outputs is confusing. |
| Dynamic introspection | To support 75+ functions without 2000 lines of manual mapping. | Manual mapping is unmaintainable. |

## Verification Plan

### Automated Tests
- `pytest tests/contract/test_phasorpy_discovery.py`: Verify function count and metadata.
- `pytest tests/integration/test_phasorpy_workflow.py`: End-to-end "Load SDT -> Phasor Transform -> Plot".

### Manual Verification
- Use `describe_function("phasorpy.phasor.phasor_from_signal")` via MCP client to verify schema correctness.
- Execute a plotting function and view the resulting PNG.
