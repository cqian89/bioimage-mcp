# Code Review: 008-api-refinement

## Review Date: 2025-12-29

### Summary Table

| Category | Status | Details |
|----------|--------|---------|
| Tasks | **PASS** | All 39 tasks marked complete in tasks.md |
| Tests | **FAIL** | 469 passed (contract/unit), 6 failed (integration) |
| Coverage | **MEDIUM** | Core functionality covered; integration tests need updates |
| Architecture | **PASS** | Follows plan.md architecture and stack choices |
| Constitution | **PASS** | All principles satisfied; no violations |

---

## Findings

### CRITICAL: None

No critical issues identified.

---

### HIGH: Integration Tests Use Legacy Function Names

**Severity**: HIGH  
**Location**: Multiple integration test files

**Description**: Six integration tests fail because they use legacy short function names (e.g., `base.gaussian`, `base.phasor_from_flim`, `base.relabel_axes`) instead of the new canonical names (e.g., `base.bioimage_mcp_base.transforms.phasor_from_flim`).

**Affected Tests**:
1. `test_discovery_enrichment.py::test_describe_function_uses_json_cache` - Uses `base.gaussian`
2. `test_flim_phasor_e2e.py::test_flim_phasor_e2e` - Uses `base.phasor_from_flim`
3. `test_live_workflow.py::test_live_workflow_project_sum_cellpose` - Uses `base.project_sum`
4. `test_mcp_test_client.py::test_mcp_test_client_list_and_search` - Asserts `base.relabel_axes` in results
5. `test_workflows.py::test_full_discovery_to_execution_flow` - Uses `base.phasor_from_flim`, `base.relabel_axes`
6. `test_workflows.py::test_flim_phasor_golden_path` - Uses `base.relabel_axes`, `base.phasor_from_flim`

**Root Cause**: Per FR-029, functions MUST use canonical `env.package.module.function` naming only. Short names/aliases are NOT supported. The manifest was updated but integration tests were not.

**Impact**: Tests fail, blocking CI/CD pipeline.

**Remediation**:

Update the affected tests to use canonical names. For example:

| Legacy Name | Canonical Name |
|-------------|----------------|
| `base.gaussian` | `base.bioimage_mcp_base.preprocess.gaussian` |
| `base.phasor_from_flim` | `base.bioimage_mcp_base.transforms.phasor_from_flim` |
| `base.project_sum` | `base.bioimage_mcp_base.transforms.project_sum` |
| `base.relabel_axes` | `base.bioimage_mcp_base.axis_ops.relabel_axes` |

Example fix for `test_workflows.py`:
```python
# Before
assert "base.phasor_from_flim" in fn_ids
mcp_test_client.activate_functions(["base.relabel_axes", "base.phasor_from_flim"])

# After
assert "base.bioimage_mcp_base.transforms.phasor_from_flim" in fn_ids
mcp_test_client.activate_functions([
    "base.bioimage_mcp_base.axis_ops.relabel_axes",
    "base.bioimage_mcp_base.transforms.phasor_from_flim"
])
```

---

### MEDIUM: None

---

### LOW: xpassed Test in Unit Tests

**Severity**: LOW  
**Location**: `tests/unit/runtimes/test_workflow_validation.py`

**Description**: One test unexpectedly passed (`xpassed`) that was marked as expected to fail. This is not a failure but should be reviewed to determine if the `xfail` marker should be removed.

**Remediation**: Review the test and remove `@pytest.mark.xfail` if the functionality is now working correctly.

---

## Task Validation Summary

All 39 tasks in `tasks.md` are marked complete (`[x]`). Key implementations verified:

### Phase 1: Setup & Data Models ✓
- T001-T005: Permission/config models defined; `builtin` directory removed

### Phase 2: Foundational ✓
- T006-T009: Base manifest updated with canonical names; placeholder modules created

### Phase 3: Permissions ✓
- T010-T016: Contract tests and `PermissionService` implemented with `inherit`, `explicit`, `hybrid` modes

### Phase 4: Unified Tool Environment ✓
- T017-T019: `builtin` removed; all functions run in `base` environment

### Phase 5: Hierarchical Discovery ✓
- T020-T024: `list_tools` supports `path`, `paths`, `flatten`, auto-expansion

### Phase 6: Multi-Keyword Search ✓
- T025-T028: `SearchIndex` with BM25 + n-gram tokenization implemented

### Phase 7: Batch Function Descriptions ✓
- T029-T031: `describe_function(fn_ids=[...])` works with backward compatibility

### Phase 8: Execution & Guidance ✓
- T032-T036: `run_function` registered; `call_tool` removed; `workflow_hint` added

### Phase 9: Polish ✓
- T037-T039: README updated with migration guide; validation script runs

---

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Stable MCP Surface | ✓ PASS | New parameters are additive; pagination preserved |
| II. Isolated Execution | ✓ PASS | Tools run in `bioimage-mcp-base`; subprocess boundaries maintained |
| III. Artifact References Only | ✓ PASS | No changes to artifact model |
| IV. Reproducibility | ✓ PASS | Permission decisions logged; provenance unchanged |
| V. Safety & Observability | ✓ PASS | `inherit` mode + Elicitation implemented; all decisions logged |
| VI. Test-Driven Development | ✓ PASS | Contract tests written before implementation |
| VII. Early Development Policy | ✓ PASS | Breaking changes acceptable pre-1.0 |

---

## Test Coverage Evaluation

### Strengths
- **Contract tests**: Comprehensive schema validation for all new models
- **Unit tests**: Good coverage of core logic (permissions, search, hierarchy)
- **Integration tests**: Cover main workflows (pending name updates)

### Gaps
- **Integration tests need update**: 6 tests use legacy names
- **Edge cases**: Could add tests for:
  - Permission fallback when client doesn't support Roots
  - Elicitation timeout handling
  - Multi-path `list_tools` with pagination

### Suggested Improvements

1. **Fix failing integration tests** (HIGH priority):
   - Update all legacy short names to canonical format

2. **Add edge case tests**:
   - Test `inherit` mode when `list_roots()` returns empty list
   - Test `on_overwrite: ask` when client doesn't support Elicitation

3. **Performance tests**:
   - Validate `list_tools` completes in <100ms per spec requirement

---

## Recommendations

1. **Immediate**: Update the 6 failing integration tests to use canonical function names
2. **Short-term**: Review and remove `xfail` marker from unexpectedly passing test
3. **Medium-term**: Add edge case tests for permission system fallbacks
4. **Long-term**: Consider adding a function name mapping/lookup for better discoverability

---

## Conclusion

The 008-api-refinement implementation is **substantially complete** with all 39 tasks implemented correctly. The architecture follows the plan, and all constitution principles are satisfied. 

**Blocking Issue**: 6 integration tests fail due to using legacy short names. These must be updated to use canonical names before merging.

**Overall Assessment**: Ready for merge after integration test fixes.
