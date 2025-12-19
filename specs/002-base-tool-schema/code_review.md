# Code Review: 002-base-tool-schema Implementation

**Reviewed Commit**: `e83bb80` (feat: implement 002-base-tool-schema)  
**Reviewer**: Automated  
**Date**: 2025-12-19  
**Spec Reference**: `specs/002-base-tool-schema/spec.md`

---

## Executive Summary

The implementation **substantially meets** the 002-base-tool-schema specification. All tasks in `tasks.md` are marked complete, 23 base functions are implemented, schema caching works correctly, and the live workflow test validates end-to-end execution. However, **one critical gap (FR-009 output isolation)** and several medium/low issues require attention before the feature can be considered complete.

| Category | Count |
|----------|-------|
| Critical Issues | 1 |
| Medium Issues | 2 |
| Low Issues | 3 |
| Tests Passing | 243/245 (2 skipped as expected) |
| Overall Coverage | 64% |

---

## Test Coverage Analysis

### Overall Coverage Metrics

| Component | Statements | Missed | Coverage |
|-----------|-----------|--------|----------|
| **Core Server (`src/bioimage_mcp/`)** | 1,182 | 261 | **78%** |
| **Base Tools (`tools/base/`)** | 442 | 442 | **0%** |
| **Total** | 1,975 | 703 | **64%** |

### Coverage by Feature Area (002-specific)

| File | Coverage | Assessment |
|------|----------|------------|
| `registry/schema_cache.py` | 75% | Good; missing tests for `invalidate_tool()` and edge cases |
| `api/discovery.py` | 88% | Good; `describe_function` enrichment path covered |
| `api/execution.py` | 91% | Good |
| `registry/manifest_schema.py` | 95% | Excellent |
| `runtimes/introspect.py` | 97% | Excellent |
| `tools/base/*` | 0% | **GAP**: No unit tests for base tool implementations |

### Test Categories for 002-base-tool-schema

| Test Type | Files | Coverage |
|-----------|-------|----------|
| **Contract Tests** | `test_base_tools.py`, `test_meta_describe_contract.py`, `test_discovery_summary_first.py` | All 24 functions discoverable; meta.describe protocol validated |
| **Integration Tests** | `test_discovery_enrichment.py`, `test_live_workflow.py` | Cache behavior verified; live E2E skips correctly when envs missing |
| **Unit Tests** | `test_introspect.py` | Introspection utilities well-tested (97%) |

### Missing Test Coverage

1. **SchemaCache Unit Tests**: No dedicated unit tests for:
   - `SchemaCache.invalidate_tool()` method
   - Edge cases: corrupt JSON, schema version mismatch, concurrent writes
   
2. **Base Tool Unit Tests**: 0% coverage for `tools/base/bioimage_mcp_base/*.py`
   - No tests for individual function implementations
   - Relies entirely on integration test (`test_live_workflow.py`) which skips when envs are missing
   
3. **Error Paths**: Limited testing for:
   - `describe_function` when `meta.describe` fails
   - Malformed/unreadable input artifacts
   - Tool timeout scenarios specific to base tools

---

## Requirements Verification

### Functional Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **FR-001**: Summary-first listing | ✅ Met | `search_functions` returns only `fn_id`, `tool_id`, `name`, `description`, `tags` |
| **FR-002**: Complete schema on describe | ✅ Met | `describe_function` returns `FunctionResponse` with full `schema` |
| **FR-003**: Local JSON cache | ✅ Met | `SchemaCache` in `schema_cache.py` with `${artifact_store_root}/state/schema_cache.json` |
| **FR-004**: Version-keyed invalidation | ✅ Met | Cache key is `{tool_id}@{tool_version}`; mismatch triggers re-enrichment |
| **FR-005**: Curated base functions | ✅ Met | 23 functions across I/O (2), transforms (8), preprocessing (13) |
| **FR-006**: Detailed descriptions | ✅ Met | `descriptions.py` contains curated parameter descriptions for all functions |
| **FR-007**: Function catalog doc | ✅ Met | `base-function-catalog.md` created and documents all functions |
| **FR-008**: Live E2E test | ✅ Met | `test_live_workflow.py` chains `base.project_sum` → `cellpose.segment` |
| **FR-009**: Output isolation | ❌ **Gap** | `work_dir` is shared across all runs (see Critical Issues) |
| **FR-010**: Combined workflows | ✅ Met | Live test uses base + cellpose in sequence |
| **FR-011**: CLI subprocess invokable | ✅ Met | `execute_tool` runs tools via subprocess |
| **FR-012**: Dataset provenance | ⚠️ Partial | `datasets/README.md` exists but contains TBD placeholders |

### Success Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **SC-001**: ≥20 functions | ✅ Met | 23 base functions (+ 1 meta.describe = 24 total) |
| **SC-002**: Cache hit behavior | ✅ Met | `test_discovery_enrichment.py` verifies second call uses cache |
| **SC-003**: Readable output artifact | ✅ Met | Live test validates `LabelImageRef` output |
| **SC-004**: Skip with reason | ✅ Met | `pytest.skip("Required tool environments missing...")` |
| **SC-005**: Discovery-to-execution flow | ✅ Met | Demonstrated in `test_mcp_llm_simulation.py` |

---

## Issues Found

### Critical

#### 1. FR-009: Output Isolation Not Fully Implemented

**Location**: `src/bioimage_mcp/api/execution.py:179`

```python
work_dir = self._config.artifact_store_root / "work" / "runs"  # SHARED!
work_dir.mkdir(parents=True, exist_ok=True)
```

**Problem**: All workflow runs share the same `work_dir`. Tool functions use hardcoded output filenames:
- `project_sum.ome.zarr`
- `gaussian.ome.zarr`
- etc.

Base tools check for file existence and raise `FileExistsError`, causing sequential runs of the same function to fail. Cellpose tools may silently overwrite. Concurrent runs will race.

**Impact**: 
- Sequential runs of the same base function fail after the first run
- Concurrent runs corrupt each other's outputs
- FR-009 explicitly requires "output-isolated" runs

**Recommendation**: Generate `run_id` early and use per-run subdirectory:
```python
import uuid
run_id = uuid.uuid4().hex
work_dir = self._config.artifact_store_root / "work" / "runs" / run_id
```

---

### Medium

#### 2. Code Duplication in Base Tools

**Locations**: 
- `tools/base/bioimage_mcp_base/io.py`
- `tools/base/bioimage_mcp_base/transforms.py`
- `tools/base/bioimage_mcp_base/preprocess.py`

**Duplicated Code**:
| Function | Copies |
|----------|--------|
| `_uri_to_path()` | 3 |
| `_load_image()` | 2 |
| `_save_zarr()` | 2 |
| `AXIS_ALIASES` | 2 (with inconsistency!) |

**Inconsistency**: `AXIS_ALIASES["c"]` is `0` in `transforms.py` but `-1` in `preprocess.py`.

**Recommendation**: Extract to `tools/base/bioimage_mcp_base/utils.py` and resolve alias inconsistency.

---

#### 3. No Unit Tests for Base Tool Implementations

**Coverage**: 0% for `tools/base/bioimage_mcp_base/*.py`

**Problem**: The 23 base functions have no unit tests. The only test exercising them is `test_live_workflow.py`, which:
- Skips when conda environments are missing
- Only tests `project_sum` (1 of 23 functions)
- Does not test error handling or edge cases

**Recommendation**: Add unit tests for each function using mocked I/O, verifying:
- Parameter validation
- Error handling (missing inputs, invalid params)
- Output structure

---

### Low

#### 4. Dataset Provenance Incomplete (FR-012)

**Location**: `datasets/README.md`

```markdown
Provenance (pending details):
- Source: TBD
- License: TBD
- Attribution: TBD
- Retrieved: TBD
```

**Recommendation**: Fill in actual provenance before release.

---

#### 5. Pydantic Warning for FunctionResponse.schema

**Location**: `src/bioimage_mcp/registry/manifest_schema.py:78`

```python
class FunctionResponse(BaseModel):
    schema: dict  # Shadows BaseModel.schema
```

**Warning**: "Field name 'schema' in 'FunctionResponse' shadows an attribute in parent 'BaseModel'"

**Recommendation**: Rename to `params_schema` for consistency with `Function` model.

---

#### 6. SchemaCache.invalidate_tool() Untested

**Location**: `src/bioimage_mcp/registry/schema_cache.py:59-66`

The `invalidate_tool()` method exists but is never called or tested. It's intended for explicit cache invalidation but the current implementation relies solely on version-key mismatches.

**Recommendation**: Either remove if unused, or add a test and document when it should be called.

---

## Positive Findings

1. **Clean Architecture**: Clear separation between manifest, descriptions, entrypoint, and ops modules
2. **Contract-Implementation Parity**: `contracts/base-manifest.yaml` matches `tools/base/manifest.yaml` exactly
3. **Comprehensive Function Set**: 23 functions spanning all required categories with curated descriptions
4. **Schema Caching Works**: Verified by integration test with mock execute_tool
5. **Proper Skip Behavior**: Live tests skip gracefully with actionable messages
6. **Good Core Coverage**: 78% on server code, with key paths well-tested

---

## Recommendations Summary

| Priority | Issue | Action | Effort |
|----------|-------|--------|--------|
| **Critical** | FR-009 output isolation | Add run-specific subdirectory to work_dir | Small |
| **Medium** | Code duplication | Extract shared utils module | Small |
| **Medium** | No base tool unit tests | Add pytest fixtures with mocked I/O | Medium |
| **Low** | Dataset provenance | Complete TBD fields | Trivial |
| **Low** | Pydantic warning | Rename `schema` → `params_schema` | Trivial |
| **Low** | Untested invalidate_tool | Add test or remove | Trivial |

---

## Verdict

The implementation is **substantially complete** with good architectural choices and working core functionality. The **critical FR-009 gap** (shared work directory) must be fixed before the feature can be merged, as it will cause deterministic failures in real-world usage. The medium-priority test coverage gaps should be addressed to ensure maintainability.

**Status**: ⚠️ **Needs Work** (1 critical, 2 medium issues)
