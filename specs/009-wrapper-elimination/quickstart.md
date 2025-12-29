# Quickstart: Wrapper Elimination Validation

**Date**: 2025-12-29  
**Purpose**: Validate implementation of wrapper elimination, overlay system, and dynamic execution.

## Prerequisites

```bash
# Ensure bioimage-mcp-base environment is installed
python -m bioimage_mcp doctor

# Run contract tests to verify baseline
pytest tests/contract/ -v
```

## Validation Steps

### 1. Overlay Model and Schema
Verify the core data models for function overlays and their merge logic.

```bash
# Unit test: Overlay model and merge logic
pytest tests/unit/registry/test_overlay_merge.py -q

# Contract test: Overlay schema validation
pytest tests/contract/test_overlay_schema.py -q
```
**Expected**: Models correctly validate against the schema and merge operations correctly override fields.

### 2. Hierarchical Listing
Verify that the registry correctly organizes functions into the new hierarchical namespace (e.g., `base.skimage.*`).

```bash
# Integration test: Hierarchical listing
pytest tests/integration/test_hierarchical_listing.py -q
```
**Expected**: `list_tools` returns a structured view of the toolbox with clear nesting and summary pagination.

### 3. Overlay Merge Discovery
Verify that dynamic discovery correctly merges static overlays (hints, tags) with dynamically introspected functions.

```bash
# Integration test: Overlay merge discovery
pytest tests/integration/test_overlay_discovery.py -q
```
**Expected**: Discovered functions like `base.skimage.filters.gaussian` have the correct `artifact_type`, `tags`, and `hints` merged from the manifest.

### 4. Wrapper Namespace & Execution
Verify that the "essential" wrappers have been moved to the `base.wrapper.*` namespace and execute correctly.

```bash
# Unit test: Wrapper module imports and manifest IDs
pytest tests/unit/base/test_wrapper_namespace.py -q

# Integration test: Execution of new wrapper functions
pytest tests/integration/test_wrapper_execution.py -q
```
**Expected**: All essential wrappers (IO, Axis ops, Phasor) are present in the new namespace and functional in a live environment.

### 5. Thin Wrappers Removed / Dynamic Execution
Verify that custom thin wrappers have been removed from the manifest and replaced by direct dynamic execution of library functions.

```bash
# Integration test: Dynamic execution of library functions
pytest tests/integration/test_dynamic_execution.py -q
```
**Expected**: Library functions (e.g., `skimage.filters.gaussian`) execute directly via the dynamic registry without custom wrapper code.

### 6. Metadata Propagation
Verify that metadata (like axis info or physical scales) propagates correctly through dynamic functions even without custom wrapper code.

```bash
# Integration test: Metadata propagation
pytest tests/integration/test_metadata_propagation.py -q
```
**Expected**: Output artifacts retain or correctly transform metadata from input artifacts.

### 7. Legacy Redirects
Verify that old function IDs correctly redirect to new wrappers or dynamic equivalents with a deprecation warning.

```bash
# Integration test: Legacy ID redirects
pytest tests/integration/test_legacy_redirects.py -q
```
**Expected**: Calls to legacy IDs (e.g., `base.bioimage_mcp_base.preprocess.denoise_image`) still work but execute their modern counterparts.

## Success Criteria Checklist

| Criterion | Validation | Status |
|-----------|------------|--------|
| SC-001: Static manifest ≤16 essential wrappers | Step 4 | ☐ |
| SC-002: Hierarchical discovery (base.skimage) | Step 2 | ☐ |
| SC-003: Overlay merge works | Step 3 | ☐ |
| SC-004: All tests pass | Full suite | ☐ |
| SC-005: Legacy redirects functional | Step 7 | ☐ |

## Troubleshooting

- **Import Errors**: Ensure you have installed the base tool environment via `python -m bioimage_mcp doctor` or manual installation.
- **Missing Functions**: Check `tools/base/manifest.yaml` for correct `dynamic_sources` and `overlays` configuration.
- **Redirection Failures**: Check the server logs for "Redirecting legacy function ID" messages to confirm routing.
