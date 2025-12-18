---

description: "Executable task list for v0.0 Bootstrap"
---

# Tasks: v0.0 Bootstrap

**Input**: Design documents from `specs/001-v0-bootstrap/`

- `specs/001-v0-bootstrap/plan.md`
- `specs/001-v0-bootstrap/spec.md`
- `specs/001-v0-bootstrap/research.md`
- `specs/001-v0-bootstrap/data-model.md`
- `specs/001-v0-bootstrap/contracts/openapi.yaml`
- `specs/001-v0-bootstrap/quickstart.md`

**Tests**: Required (spec.md includes mandatory user scenarios & testing).

## Checklist Format (enforced)

Every task MUST use:

```text
Example: - [ ] T000 [P] [USX] Implement doctor command in src/bioimage_mcp/bootstrap/doctor.py
```

## Path Conventions (this repo)

- Python package code: `src/bioimage_mcp/`
- Tests: `tests/`
- Tool packs (data-plane): `tools/`
- Conda/micromamba env specs: `envs/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create a runnable Python project skeleton with a CLI entrypoint.

- [x] T001 Create package skeleton under src/bioimage_mcp/ (create src/bioimage_mcp/__init__.py, src/bioimage_mcp/api/__init__.py, src/bioimage_mcp/artifacts/__init__.py, src/bioimage_mcp/bootstrap/__init__.py, src/bioimage_mcp/config/__init__.py, src/bioimage_mcp/registry/__init__.py, src/bioimage_mcp/runtimes/__init__.py, src/bioimage_mcp/runs/__init__.py)
- [x] T002 Define project packaging and runtime dependencies in pyproject.toml (python>=3.13, mcp, pydantic>=2, pyyaml, bioio, bioio-ome-zarr, bioio-ome-tiff, ngff-zarr)
- [x] T003 [P] Configure ruff + pytest defaults (add ruff config in ruff.toml and pytest config in pytest.ini)
- [x] T004 Implement CLI entrypoint skeleton in src/bioimage_mcp/cli.py (subcommands: install, doctor, configure, serve; include --help)
- [x] T005 [P] Add __main__ entry to support python -m bioimage_mcp in src/bioimage_mcp/__main__.py
- [x] T006 [P] Add initial test scaffolding in tests/conftest.py and a smoke import test in tests/unit/test_imports.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared primitives needed by ALL user stories (config, filesystem policy, pagination, storage, logging).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Implement structured logging setup in src/bioimage_mcp/logging.py (module-level get_logger(), consistent formatting, CLI-friendly output)
- [x] T008 Implement shared error types in src/bioimage_mcp/errors.py (user-facing vs internal errors; include error codes for doctor/run failures)
- [x] T009 Implement Config schema models in src/bioimage_mcp/config/schema.py (fields from specs/001-v0-bootstrap/data-model.md: artifact_store_root, tool_manifest_roots, fs_allowlist_read/write, fs_denylist, default/max pagination limits)
- [x] T010 Implement layered YAML config loader in src/bioimage_mcp/config/loader.py (load ~/.bioimage-mcp/config.yaml then .bioimage-mcp/config.yaml; local overrides global; validate with Pydantic; normalize absolute paths)
- [x] T011 Implement filesystem allow/deny enforcement helpers in src/bioimage_mcp/config/fs_policy.py (denylist overrides; validate read/write roots; helper: assert_path_allowed(operation, path, config))
- [x] T012 Implement opaque cursor pagination helpers in src/bioimage_mcp/api/pagination.py (encode/decode cursor; enforce default and max limits from config)
- [x] T013 Implement SQLite storage bootstrap in src/bioimage_mcp/storage/sqlite.py (create/open DB file under artifact_store_root or a dedicated state dir; create tables for tools/functions/artifacts/runs/diagnostics)
- [x] T014 [P] Add unit tests for config loading and merging in tests/unit/config/test_loader.py
- [x] T015 [P] Add unit tests for fs policy allow/deny behavior in tests/unit/config/test_fs_policy.py
- [x] T016 [P] Add unit tests for cursor pagination encode/decode in tests/unit/api/test_pagination.py

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 — Install and verify locally (Priority: P1) 🎯 MVP

**Goal**: A new user can install Bioimage-MCP and run an 8-check readiness/doctor flow with actionable remediation.

**Independent Test**: On a clean machine or clean environment, run `bioimage-mcp install --profile cpu` then `bioimage-mcp doctor` and confirm output is either “ready” or a per-check remediation list.

### Tests for User Story 1

- [x] T017 [P] [US1] Add unit tests for doctor output shape and remediation messages in tests/unit/bootstrap/test_doctor_output.py
- [x] T018 [P] [US1] Add unit tests for the 8 prerequisite checks in tests/unit/bootstrap/test_checks.py (Python version, micromamba/conda, disk, permissions, base env, GPU, conda-lock, network)
- [x] T019 [P] [US1] Add CLI integration tests for install/doctor command wiring in tests/integration/test_cli_doctor_install.py (use monkeypatch to avoid real conda calls)

### Implementation for User Story 1

- [x] T020 [P] [US1] Implement env manager detection in src/bioimage_mcp/bootstrap/env_manager.py (prefer micromamba; fallback to conda/mamba; detect executable and version)
- [x] T021 [P] [US1] Implement prerequisite checks in src/bioimage_mcp/bootstrap/checks.py (8 checks; each returns status + remediation list + optional details)
- [x] T022 [US1] Implement doctor command in src/bioimage_mcp/bootstrap/doctor.py (runs all checks; prints summary; nonzero exit when not ready; optional --json output)
- [x] T023 [US1] Implement install command in src/bioimage_mcp/bootstrap/install.py (profiles: cpu/gpu; creates/updates base env bioimage-mcp-base from envs/bioimage-mcp-base.yaml; prints next steps)
- [x] T024 [P] [US1] Add base environment spec in envs/bioimage-mcp-base.yaml (pin core deps needed for built-ins; document linux-64)
- [x] T025 [US1] Implement configure command in src/bioimage_mcp/bootstrap/configure.py (write a starter .bioimage-mcp/config.yaml; ensure absolute paths)
- [x] T026 [US1] Wire install/doctor/configure into top-level CLI in src/bioimage_mcp/cli.py
- [x] T027 [US1] Document install + doctor usage and troubleshooting in README.md (include the 8 checks and remediation guidance)

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 — Start server and discover tools on demand (Priority: P2)

**Goal**: A user starts the MCP server and discovers tools/functions via paginated list/search/describe (summary-first; full schema only via describe).

**Independent Test**: Start the server with a small tool manifest directory and verify list/search/describe behave correctly with pagination, keyword search, tag filtering, and invalid-manifest exclusion.

### Tests for User Story 2

- [x] T028 [P] [US2] Add contract-shape tests for discovery responses in tests/contract/test_discovery_contract.py (align with specs/001-v0-bootstrap/contracts/openapi.yaml)
- [x] T029 [P] [US2] Add unit tests for manifest validation and invalid-manifest diagnostics in tests/unit/registry/test_manifest_validation.py
- [x] T030 [P] [US2] Add unit tests for registry pagination and search behavior in tests/unit/registry/test_registry_queries.py

### Implementation for User Story 2

- [x] T031 [P] [US2] Implement ToolManifest + Function schema models in src/bioimage_mcp/registry/manifest_schema.py (Pydantic v2; fields from specs/001-v0-bootstrap/data-model.md)
- [x] T032 [P] [US2] Implement manifest diagnostics model in src/bioimage_mcp/registry/diagnostics.py (path, tool_id?, errors[])
- [x] T033 [US2] Implement YAML manifest loader in src/bioimage_mcp/registry/loader.py (discover under Config.tool_manifest_roots; validate; compute manifest checksum; emit diagnostics for invalid)
- [x] T034 [US2] Implement registry indexer backed by SQLite in src/bioimage_mcp/registry/index.py (upsert tools/functions; enforce unique tool_id and fn_id; store diagnostics)
- [x] T035 [P] [US2] Implement keyword + tag + io-type search query builder in src/bioimage_mcp/registry/search.py (return FunctionSummary rows; enforce pagination limits)
- [x] T036 [US2] Implement discovery service layer in src/bioimage_mcp/api/discovery.py (list_tools, describe_tool, search_functions, describe_function; summary-first)
- [x] T037 [US2] Implement MCP server wiring in src/bioimage_mcp/api/server.py (register discovery tools with MCP Python SDK; bind to registry + config)
- [x] T038 [US2] Implement serve command in src/bioimage_mcp/bootstrap/serve.py (bioimage-mcp serve --stdio; loads config; initializes registry; starts MCP server)
- [x] T039 [US2] Wire serve into top-level CLI in src/bioimage_mcp/cli.py

**Checkpoint**: User Story 2 is fully functional and independently testable.

---

## Phase 5: User Story 3 — Run a trivial built-in function end-to-end (Priority: P3)

**Goal**: Execute two built-in functions end-to-end via artifact references, producing output artifacts, run records, and log artifacts; support artifact metadata and export.

**Format note**: The v0.0 implementation uses `builtin.convert_to_ome_zarr` and writes OME-Zarr outputs. The format strategy has since pivoted to OME-TIFF as the default intermediate; the migration is tracked as v0.1 work.

**Independent Test (v0.0)**: With allowlisted input/output roots configured, run `builtin.convert_to_ome_zarr` and `builtin.gaussian_blur` on a small sample image and verify (1) run succeeds, (2) output ArtifactRef is returned, (3) artifact metadata is retrievable without pixel transfer, (4) export creates a file/dir matching recorded checksum, (5) failure paths still produce a LogRef.

### Tests for User Story 3

- [x] T040 [P] [US3] Add contract-shape tests for execution + artifact responses in tests/contract/test_execution_artifacts_contract.py (align with specs/001-v0-bootstrap/contracts/openapi.yaml)
- [x] T041 [P] [US3] Add unit tests for ArtifactRef checksum calculation in tests/unit/artifacts/test_checksums.py (file and directory tree-hash)
- [x] T042 [P] [US3] Add unit tests for artifact store persistence and metadata extraction in tests/unit/artifacts/test_store.py
- [x] T043 [P] [US3] Add unit tests for run record lifecycle and log refs in tests/unit/runs/test_run_store.py
- [x] T044 [US3] Add integration test for 1-step run_workflow using a test tool pack in tests/integration/test_run_workflow_e2e.py (exec via subprocess shim; uses temp dirs; validates outputs + logs)

### Implementation for User Story 3

- [x] T045 [P] [US3] Implement ArtifactRef models in src/bioimage_mcp/artifacts/models.py (BioImageRef + LogRef minimum metadata per specs/001-v0-bootstrap/research.md)
- [x] T046 [P] [US3] Implement checksum utilities in src/bioimage_mcp/artifacts/checksums.py (sha256 for files; deterministic sha256-tree for directories)
- [x] T047 [US3] Implement artifact store in src/bioimage_mcp/artifacts/store.py (persist artifacts + metadata; assign ref_id; enforce fs_policy; store index rows in SQLite)
- [x] T048 [P] [US3] Implement image metadata extraction in src/bioimage_mcp/artifacts/metadata.py (axes/shape/dtype/channel names/physical pixel sizes via bioio)
- [x] T049 [P] [US3] Implement Run + Provenance models in src/bioimage_mcp/runs/models.py (status lifecycle; log_ref; inputs/outputs; provenance)
- [x] T050 [US3] Implement run store in src/bioimage_mcp/runs/store.py (create run_id; persist status transitions; link outputs + log_ref; persist errors)
- [x] T051 [P] [US3] Define subprocess shim protocol in src/bioimage_mcp/runtimes/protocol.py (JSON-in/JSON-out; maps fn_id + params + input ArtifactRefs to outputs + logs)
- [x] T052 [US3] Implement runtime executor in src/bioimage_mcp/runtimes/executor.py (run tool entrypoint inside env_id via micromamba/conda; capture stdout/stderr; timeouts; always produce LogRef)
- [x] T053 [P] [US3] Add built-in tool manifest in tools/builtin/manifest.yaml (tool_id, tool_version, env_id=bioimage-mcp-base, entrypoint, functions: builtin.gaussian_blur and builtin.convert_to_ome_zarr)
- [x] T054 [P] [US3] Implement built-in tool pack entrypoint in tools/builtin/bioimage_mcp_builtin/entrypoint.py (parse protocol request; dispatch to ops; write protocol response)
- [x] T055 [P] [US3] Implement Gaussian blur op in tools/builtin/bioimage_mcp_builtin/ops/gaussian_blur.py (read BioImageRef; apply blur; write OME-Zarr output)
- [x] T056 [P] [US3] Implement convert-to-OME-Zarr op in tools/builtin/bioimage_mcp_builtin/ops/convert_to_ome_zarr.py (read via bioio; write via ngff-zarr)
- [x] T057 [US3] Implement workflow execution service in src/bioimage_mcp/api/execution.py (run_workflow for 1-step; resolve fn_id via registry; call executor; persist Run + outputs)
- [x] T058 [P] [US3] Implement artifact metadata API in src/bioimage_mcp/api/artifacts.py (get_artifact(ref_id) returns metadata only; bounded)
- [x] T059 [US3] Implement artifact export in src/bioimage_mcp/artifacts/export.py (copy file/dir to dest_path; enforce fs_allowlist_write; verify checksum)
- [x] T060 [US3] Wire execution + artifact APIs into MCP server in src/bioimage_mcp/api/server.py (register run_workflow, get_run_status, get_artifact, export_artifact)

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, observability, performance, and documentation that spans multiple stories.

- [x] T061 [P] Add end-to-end quickstart validation script in scripts/validate_quickstart.sh (runs the commands in specs/001-v0-bootstrap/quickstart.md against a local temp workspace)
- [x] T062 [P] Improve user-facing error messages and exit codes across CLI commands in src/bioimage_mcp/cli.py
- [x] T063 [P] Add bounded diagnostics surfacing (invalid manifests, registry stats) to doctor output in src/bioimage_mcp/bootstrap/doctor.py
- [x] T064 [P] Add performance sanity checks for discovery queries in tests/integration/test_discovery_perf.py (skip by default; document thresholds)
- [x] T065 Update specs/001-v0-bootstrap/quickstart.md examples if CLI flags or names differ after implementation
- [x] T066 [P] [US1] Add test for GPU detection on headless/no-GPU machines in tests/unit/bootstrap/test_checks.py (verify graceful degradation and clear messaging)
- [x] T067 [P] [US3] Add test for disk-full error handling in tests/unit/artifacts/test_store_errors.py (simulate ENOSPC; verify graceful error and log persistence)
- [x] T068 [P] [US3] Add test for tool timeout enforcement in tests/unit/runtimes/test_executor_timeout.py (verify timeout triggers, process killed, LogRef still produced)
- [x] T069 [P] [US3] Add integration test for filesystem policy enforcement in tests/integration/test_fs_policy_enforcement.py (attempt reads/writes outside allowlist; verify denial and error message)

---

## Dependencies & Execution Order

### User Story Dependency Graph

- **Phase 1 (Setup)** → **Phase 2 (Foundational)** → **US1 (P1)** → **US2 (P2)** → **US3 (P3)** → **Polish**

Rationale:
- US1 establishes install/readiness and config required for reliable execution.
- US2 depends on config + registry initialization patterns and delivers the stable discovery-first interface.
- US3 depends on registry + server surface and adds artifact/run execution end-to-end.

---

## Parallel Execution Examples (per user story)

### US1 parallelizable groups

- Checks + doctor plumbing can proceed alongside env manager detection.
- Tests for each prerequisite check can be authored independently.

### US2 parallelizable groups

- Manifest schema (Pydantic) can be built in parallel with diagnostics + search query builder.
- Tests for pagination/search can be built in parallel with loader/index work.

### US3 parallelizable groups

- Artifact checksums, artifact models, run models, and protocol definition can be done in parallel.
- Built-in ops (blur vs convert) can be implemented independently once protocol is stable.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup + Foundational.
2. Complete US1 (install/configure/doctor).
3. **Stop and validate**: Run US1 independent test scenarios from `specs/001-v0-bootstrap/spec.md`.

### Incremental Delivery

- Add US2 (server + discovery) next and validate pagination and invalid-manifest handling.
- Add US3 last (artifacts + runs + execution) and validate end-to-end with `specs/001-v0-bootstrap/quickstart.md`.
