# Tasks: Pandas Functions for Tabular Data

**Input**: Design documents from `/specs/021-pandas-functions/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Included following TDD principles - tests are written first and must fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source code**: `src/bioimage_mcp/`, `tools/base/bioimage_mcp_base/`
- **Tests**: `tests/unit/`, `tests/contract/`, `tests/integration/`
- **Config**: `envs/`, `tools/base/manifest.yaml`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment preparation and basic project structure

- [ ] T001 Add `pandas` and `numexpr` to `envs/bioimage-mcp-base.yaml`
- [ ] T002 Update `bioimage-mcp-base` conda environment with new dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation (TDD - write first, must fail) ⚠️

- [ ] T003 [P] Contract test for pandas allowlist/denylist + discovery count (≥50 allowed functions) in `tests/contract/test_pandas_allowlists.py` (also asserts denylisted methods are not discoverable)
- [ ] T004 [P] Unit test for PandasAdapter core execution logic in `tests/unit/registry/test_pandas_adapter.py` (dispatch, ObjectRef lookup, denylisted method → structured error)
- [ ] T005 [P] Contract test for TableRef/ObjectRef/GroupByRef schemas in `tests/contract/test_pandas_artifacts.py`

### Implementation for Foundation

- [ ] T006 [P] Create `src/bioimage_mcp/registry/dynamic/pandas_allowlists.py` with categories: DATAFRAME_CLASS (optional TableRef→ObjectRef), DATAFRAME_METHODS (query accepts TableRef directly), GROUPBY_METHODS, TOPLEVEL_FUNCTIONS, and DENYLIST
- [ ] T007 [P] Create `src/bioimage_mcp/registry/dynamic/pandas_adapter.py` with core execution logic (object cache, method dispatch)
- [ ] T008 Create `src/bioimage_mcp/registry/dynamic/adapters/pandas.py` implementing BaseAdapter interface (depends on T006, T007)
- [ ] T009 Register PandasAdapterForRegistry in `src/bioimage_mcp/registry/dynamic/adapters/__init__.py`
- [ ] T010 Add `pandas` to `dynamic_sources` in `tools/base/manifest.yaml`

**Checkpoint**: Foundation ready - pandas adapter registered, allowlists defined, user story implementation can begin

---

## Phase 3: User Story 1 - Load Cellpose Measurement CSV (Priority: P1) 🎯 MVP

**Goal**: Load CSV/TSV measurement files into TableRef with column metadata and auto-delimiter detection

**Independent Test**: Provide sample CSV, verify TableRef returned with correct columns, dtypes, row_count

### Tests for User Story 1 (TDD - write first, must fail) ⚠️

- [ ] T011 [P] [US1] Contract test for `base.io.table.load` schema in `tests/contract/test_table_io.py`
- [ ] T012 [P] [US1] Unit test for table_load function in `tests/unit/ops/test_table_load.py` (CSV load, delimiter auto-detect incl comma/tab/semicolon, path allowlist validation with structured error shape + permission decision logging)
- [ ] T013 [P] [US1] Integration test loading sample CSV in `tests/integration/test_table_load.py` (optionally asserts SC-001 load ≤5s for ~10MB input under a `slow` marker)

### Implementation for User Story 1

- [ ] T014 [US1] Implement `table_load` function in `tools/base/bioimage_mcp_base/ops/io.py` (CSV/TSV delimited load with auto-delimiter detection incl comma/tab/semicolon; return structured errors on failure)
- [ ] T015 [US1] Define `base.io.table.load` in `tools/base/manifest.yaml` functions section
- [ ] T016 [US1] Add path validation against `filesystem.allowed_read` in table_load, emitting permission decision logs (allow/deny with path + reason) and structured errors on deny
- [ ] T017 [US1] Add encoding parameter support (UTF-8, latin-1, cp1252) for table_load
- [ ] T018 [US1] Add NA value specification parameter for table_load

**Checkpoint**: User Story 1 complete - CSV/TSV files can be loaded as TableRef with metadata

---

## Phase 4: User Story 2 - Filter Cells by Measurement Thresholds (Priority: P1)

**Goal**: Filter DataFrame using pandas `query()` with audit logging

**Independent Test**: Load sample table, apply filter query, verify row count and values match expectations

### Tests for User Story 2 (TDD - write first, must fail) ⚠️

- [ ] T019 [P] [US2] Contract test for `base.pandas.DataFrame.query` schema in `tests/contract/test_pandas_query.py`
- [ ] T020 [P] [US2] Unit test for DataFrame.query execution in `tests/unit/registry/test_pandas_query.py` (single + compound filters, invalid syntax → structured error, audit logging fields, and `@var` local variable access blocked)
- [ ] T021 [P] [US2] Integration test for filter workflow in `tests/integration/test_pandas_filter.py`

### Implementation for User Story 2

- [ ] T022 [US2] Implement `base.pandas.DataFrame` (TableRef → ObjectRef) as an optional convenience, and ensure `base.pandas.DataFrame.query` accepts TableRef directly via auto-coercion (reusing ObjectRef when provided)
- [ ] T023 [US2] Implement `base.pandas.DataFrame.query` with expression execution in pandas_adapter.py
- [ ] T024 [US2] Add audit logging for all query() expressions (expression, input ref_id, result row count)
- [ ] T025 [US2] Block `@var` local variable access in query expressions for isolation
- [ ] T026 [US2] Implement OBJECT_CACHE for in-memory DataFrame storage

**Checkpoint**: User Story 2 complete - DataFrames can be filtered using query() with full audit trail

---

## Phase 5: User Story 3 - Aggregate Measurements by Condition (Priority: P2)

**Goal**: Group cells by experimental condition and compute summary statistics

**Independent Test**: Group sample dataset by categorical column, verify aggregated statistics match expected values

### Tests for User Story 3 (TDD - write first, must fail) ⚠️

- [ ] T027 [P] [US3] Contract test for `base.pandas.DataFrame.groupby` and `base.pandas.GroupBy.mean/agg` in `tests/contract/test_pandas_groupby.py`
- [ ] T028 [P] [US3] Unit test for groupby and aggregation in `tests/unit/registry/test_pandas_groupby.py` (includes missing groupby column → structured error listing available columns)
- [ ] T029 [P] [US3] Integration test for groupby workflow in `tests/integration/test_pandas_groupby.py`

### Implementation for User Story 3

- [ ] T030 [US3] Implement `base.pandas.DataFrame.groupby` returning GroupByRef in pandas_adapter.py
- [ ] T031 [US3] Implement `base.pandas.GroupBy.mean` accepting GroupByRef in pandas_adapter.py
- [ ] T032 [US3] Implement `base.pandas.GroupBy.agg` with func list parameter in pandas_adapter.py
- [ ] T033 [US3] Add GroupByRef to OBJECT_CACHE with grouped_by and groups_count metadata

**Checkpoint**: User Story 3 complete - Data can be grouped and aggregated by condition

---

## Phase 6: User Story 4 - Export Filtered Results (Priority: P2)

**Goal**: Export TableRef or ObjectRef to CSV/TSV (delimited) files

**Independent Test**: Export sample DataFrame to CSV, verify file contents match data

### Tests for User Story 4 (TDD - write first, must fail) ⚠️

- [ ] T034 [P] [US4] Contract test for `base.io.table.export` schema in `tests/contract/test_table_export.py`
- [ ] T035 [P] [US4] Unit test for table_export function in `tests/unit/ops/test_table_export.py` (CSV + TSV formats, float precision, structured error on invalid destination / denied write)
- [ ] T036 [P] [US4] Integration test for export workflow in `tests/integration/test_table_export.py`

### Implementation for User Story 4

- [ ] T037 [US4] Implement `table_export` function in `tools/base/bioimage_mcp_base/ops/io.py` (enforce `filesystem.allowed_write`, log allow/deny/ask decisions with path+reason, structured errors on deny/overwrite)
- [ ] T038 [US4] Define `base.io.table.export` in `tools/base/manifest.yaml` functions section
- [ ] T039 [US4] Add numeric precision preservation (15 significant digits) for float export
- [ ] T040 [US4] Add delimiter parameter support (comma, tab) for table_export

**Checkpoint**: User Story 4 complete - Results can be exported to various formats

---

## Phase 7: User Story 5 - Merge Measurement Tables (Priority: P3)

**Goal**: Join tables from multiple sources by common key columns

**Independent Test**: Provide two tables with common key, verify merged result contains columns from both

### Tests for User Story 5 (TDD - write first, must fail) ⚠️

- [ ] T041 [P] [US5] Contract test for `base.pandas.merge` schema in `tests/contract/test_pandas_merge.py`
- [ ] T042 [P] [US5] Unit test for merge function in `tests/unit/registry/test_pandas_merge.py` (inner, left, right, outer joins)
- [ ] T043 [P] [US5] Integration test for merge workflow in `tests/integration/test_pandas_merge.py`

### Implementation for User Story 5

- [ ] T044 [US5] Implement `base.pandas.merge` in pandas_adapter.py
- [ ] T045 [US5] Implement `base.pandas.concat` for axis-based concatenation in pandas_adapter.py
- [ ] T046 [US5] Add structured error handling for missing key columns with available column list and actionable hint

**Checkpoint**: User Story 5 complete - Tables can be merged by key columns

---

## Phase 8: User Story 6 - Multi-Step Pandas Chaining (Priority: P3)

**Goal**: Enable ObjectRef chaining for complex multi-operation workflows

**Independent Test**: Execute 5+ operation chain, verify final exported table matches expected results

### Tests for User Story 6 (TDD - write first, must fail) ⚠️

- [ ] T047 [P] [US6] Integration test for full chain: load → filter → groupby → mean → export in `tests/integration/test_pandas_pipeline.py` (optionally asserts SC-003 end-to-end ≤30s under a `slow` marker)
- [ ] T048 [P] [US6] Unit test for ObjectRef chaining (10+ operations) in `tests/unit/registry/test_pandas_chaining.py`

### Implementation for User Story 6

- [ ] T049 [US6] Implement `to_tableref` operation to materialize ObjectRef to TableRef in pandas_adapter.py
- [ ] T050 [US6] Add LRU eviction with warning for OBJECT_CACHE when memory limit reached
- [ ] T051 [US6] Add ObjectRef expiration structured error (code/message/details with hint) with re-run suggestion
- [ ] T052 [US6] Verify ObjectRef chaining works for 10+ sequential operations

**Checkpoint**: User Story 6 complete - Complex workflows can be executed as chains

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T053 [P] Add additional DATAFRAME_METHODS to allowlist: `filter`, `head`, `tail`, `sample`, `fillna`, `dropna`, `replace`, `sort_values`, `reset_index`
- [ ] T054 [P] Add additional GROUPBY_METHODS to allowlist: `sum`, `count`, `min`, `max`, `std`, `var`, `describe`
- [ ] T055 [P] Implement restricted `apply()` with numpy function whitelist (log, sqrt, exp, abs) in pandas_adapter.py
- [ ] T056 [P] Add large file warning (>100MB) for table_load
- [ ] T057 [P] Add empty file handling (headers only → row_count=0)
- [ ] T058 [P] Run quickstart.md validation with sample Cellpose measurement file
- [ ] T059 Update environment lockfile with conda-lock for reproducibility
- [ ] T060 Add performance validation: 100,000-row table filter in <2 seconds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (Load): No story dependencies
  - US2 (Filter): Depends on US1 (needs loaded table)
  - US3 (Aggregate): Depends on US2 (needs ObjectRef from filter)
  - US4 (Export): Depends on US1 (needs TableRef/ObjectRef)
  - US5 (Merge): Depends on US1 (needs loaded tables)
  - US6 (Chaining): Depends on US1-US4 (validates full workflow)
- **Polish (Phase 9)**: Depends on all P1/P2 user stories being complete

### User Story Dependencies

```
Setup → Foundational → ┬→ US1 (Load) ────────┬→ US4 (Export)
                       │                     │
                       │                     └→ US5 (Merge)
                       │
                       └→ US2 (Filter) ──────→ US3 (Aggregate)
                                             │
                                             └→ US6 (Chaining)
```

### Within Each User Story (TDD Order)

1. **RED**: Write tests first (T0XX tests) - ensure they FAIL
2. **GREEN**: Implement minimum code to pass tests
3. **REFACTOR**: Improve while keeping tests green
4. Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks can run sequentially (environment dependencies)
- All Foundational tests marked [P] can run in parallel
- All Foundational implementation marked [P] can run in parallel
- Once Foundational completes:
  - US1 and US2 can start in parallel (different files)
  - US4 and US5 can start once US1 completes (different files)
- All tests within a story marked [P] can run in parallel
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD - must fail first):
Task: "Contract test for base.io.table.load in tests/contract/test_table_io.py"
Task: "Unit test for table_load in tests/unit/ops/test_table_load.py"
Task: "Integration test loading sample CSV in tests/integration/test_table_load.py"

# After tests fail, implement (sequential - same file dependencies):
Task: "Implement table_load in tools/base/bioimage_mcp_base/ops/io.py"
Task: "Define base.io.table.load in tools/base/manifest.yaml"
```

---

## Parallel Example: Foundation

```bash
# Launch all foundation tests together (TDD - must fail first):
Task: "Contract test for pandas allowlists in tests/contract/test_pandas_allowlists.py"
Task: "Unit test for PandasAdapter in tests/unit/registry/test_pandas_adapter.py"
Task: "Contract test for artifact schemas in tests/contract/test_pandas_artifacts.py"

# After tests fail, implement in parallel (different files):
Task: "Create pandas_allowlists.py"
Task: "Create pandas_adapter.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Load CSV)
4. Complete Phase 4: User Story 2 (Filter)
5. **STOP and VALIDATE**: Test load → filter workflow independently
6. Deploy/demo if ready - users can load and filter tables

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Load) → Test independently → **Increment 1**
3. Add User Story 2 (Filter) → Test independently → **Increment 2 (MVP!)**
4. Add User Story 3 (Aggregate) + US4 (Export) → **Increment 3**
5. Add User Story 5 (Merge) + US6 (Chaining) → **Increment 4 (Full Feature)**
6. Complete Polish → **Final Release**

### TDD Workflow Per Story

```
1. Write test → Run test → Confirm FAIL (RED)
2. Write minimum implementation → Run test → Confirm PASS (GREEN)
3. Refactor if needed → Run test → Confirm still PASS
4. Commit and move to next task
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD is MANDATORY**: Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All `query()` operations must be logged for audit (Constitution requirement)
- Use OBJECT_CACHE for in-memory DataFrames (research.md decision)
- Block dangerous pandas methods per denylist (research.md decision)
