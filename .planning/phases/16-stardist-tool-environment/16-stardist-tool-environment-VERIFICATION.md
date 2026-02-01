---
phase: 16-stardist-tool-environment
verified: 2026-02-01T21:20:00Z
status: human_needed
score: 6/14 must-haves verified
re_verification:
  previous_status: human_needed
  previous_score: 4/11
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Install StarDist env from lockfile"
    expected: "conda-lock install -n bioimage-mcp-stardist envs/bioimage-mcp-stardist.lock.yml completes without solver errors"
    why_human: "Requires conda/micromamba and network access"
  - test: "Run StarDist tool pack meta.list in env"
    expected: "meta.list returns StarDist callables (from_pretrained, predict_instances) with io_pattern values"
    why_human: "Requires executing entrypoint inside the stardist environment"
  - test: "Run StarDist tool pack meta.describe in env"
    expected: "meta.describe returns params_schema + tool_version + introspection_source"
    why_human: "Requires runtime introspection in isolated environment"
  - test: "Execute StarDist workflow (ObjectRef + predict_instances)"
    expected: "from_pretrained returns ObjectRef and predict_instances outputs LabelImageRef (OME-Zarr) + details JSON"
    why_human: "Requires runtime execution with TensorFlow/StarDist installed"
  - test: "Run StarDist contract + integration tests"
    expected: "Contract tests pass; integration test passes when env installed"
    why_human: "Tests must be executed under proper environments"
---

# Phase 16: StarDist Tool Environment Verification Report

**Phase Goal:** Add StarDist to the list of tool environments with dynamic function/class discovery through the unified introspection engine, following the Cellpose integration pattern.
**Verified:** 2026-02-01T21:20:00Z
**Status:** human_needed
**Re-verification:** Yes — previous verification existed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A reproducible 'bioimage-mcp-stardist' environment can be installed from repo state. | ? UNCERTAIN | `envs/bioimage-mcp-stardist.yaml` + lockfile exist, but install not executed. |
| 2 | The StarDist tool environment contains StarDist + TensorFlow + bioio OME-Zarr support. | ✓ VERIFIED | `envs/bioimage-mcp-stardist.yaml` includes `stardist=0.9.2`, `csbdeep=0.8.2`, `tensorflow-cpu>=2.15`, `bioio-ome-zarr`. |
| 3 | bioimage-mcp registry can load a StarDist tool manifest without errors. | ? UNCERTAIN | Manifest present; validation not executed. |
| 4 | Runtime meta.list can discover StarDist classes/methods from inside the tool env. | ? UNCERTAIN | `entrypoint.handle_meta_list` + adapter implemented; requires runtime execution. |
| 5 | Runtime meta.describe returns a valid params_schema for a StarDist callable. | ? UNCERTAIN | `entrypoint.handle_meta_describe` implemented; requires runtime execution. |
| 6 | A user can initialize a StarDist model and reuse it via ObjectRef across calls. | ? UNCERTAIN | Object cache + ObjectRef wiring present; requires runtime execution. |
| 7 | A user can run StarDist predict_instances and receive both label image and details outputs. | ? UNCERTAIN | `run_predict` returns labels/details; needs runtime execution. |
| 8 | Label outputs are produced as OME-Zarr (LabelImageRef) using bioio writers. | ✓ VERIFIED | `ops/predict.py` uses `OMEZarrWriter` and returns `LabelImageRef` with `format: OME-Zarr`. |
| 9 | Contract tests validate the StarDist manifest shape and meta.describe payload. | ? UNCERTAIN | Contract tests exist but were not run. |
|10 | Integration test can run (when env installed) and exercises discovery + a minimal inference path. | ? UNCERTAIN | Env-gated E2E test exists; requires runtime execution. |
|11 | Docs list StarDist as an optional tool environment. | ✓ VERIFIED | `docs/reference/tools.md` includes `Tools.StarDist` section. |
|12 | StarDist E2E integration test runs from the core server env and never imports StarDist/tool entrypoint directly. | ✓ VERIFIED | `tests/integration/test_stardist_adapter_e2e.py` uses `execute_step` and has no direct StarDist imports. |
|13 | The StarDist E2E test exercises real tool execution via subprocess worker path. | ✓ VERIFIED | Test uses `execute_step` + `worker_manager` and asserts worker is alive. |
|14 | The E2E test performs a real two-step flow: from_pretrained -> predict_instances with worker reuse. | ✓ VERIFIED | Test runs two steps and asserts PID reuse across steps. |

**Score:** 6/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---------|----------|--------|---------|
| `envs/bioimage-mcp-stardist.yaml` | Conda env definition | ✓ VERIFIED | 26 lines, contains StarDist + TF + bioio deps. |
| `envs/bioimage-mcp-stardist.lock.yml` | Pinned lockfile | ✓ VERIFIED | Non-empty conda-lock output. |
| `tools/stardist/manifest.yaml` | ToolManifest for stardist | ✓ VERIFIED | Defines env_id, entrypoint, dynamic_sources, functions. |
| `tools/stardist/bioimage_mcp_stardist/entrypoint.py` | Worker entrypoint | ✓ VERIFIED | Substantive NDJSON worker + meta.list/describe + execute routing. |
| `tools/stardist/bioimage_mcp_stardist/dynamic_discovery.py` | Discovery adapter | ✓ VERIFIED | StarDistAdapter implements discover; io_pattern set. |
| `tools/stardist/bioimage_mcp_stardist/ops/predict.py` | Inference + artifacts | ✓ VERIFIED | Produces OME-Zarr labels + JSON details. |
| `tests/contract/test_stardist_manifest_contract.py` | Manifest contract tests | ✓ VERIFIED | Present and substantive. |
| `tests/contract/test_stardist_meta_describe.py` | meta.describe contract tests | ✓ VERIFIED | Present and substantive. |
| `tests/integration/test_stardist_adapter_e2e.py` | E2E integration test | ✓ VERIFIED | Core-env execution via persistent worker. |
| `docs/reference/tools.md` | Docs mention StarDist | ✓ VERIFIED | Tools.StarDist section present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `envs/bioimage-mcp-stardist.yaml` | `envs/bioimage-mcp-stardist.lock.yml` | conda-lock | ✓ VERIFIED | Lockfile exists for the env spec. |
| `tools/stardist/manifest.yaml` | `bioimage_mcp_stardist/entrypoint.py` | entrypoint field | ✓ VERIFIED | `entrypoint: bioimage_mcp_stardist/entrypoint.py`. |
| `tools/stardist/manifest.yaml` | `dynamic_discovery.py` | dynamic_sources.adapter | ✓ VERIFIED | `adapter: stardist` present. |
| `entrypoint.py` | `ops/predict.py` | execute routing | ✓ VERIFIED | `_execute_stardist_function` calls `run_predict`. |
| `tests/integration/test_stardist_adapter_e2e.py` | `envs/bioimage-mcp-stardist.yaml` | requires_env marker | ✓ VERIFIED | `@pytest.mark.requires_env("bioimage-mcp-stardist")`. |
| `tests/integration/test_stardist_adapter_e2e.py` | `src/bioimage_mcp/runtimes/persistent.py` | worker manager path | ✓ VERIFIED | Uses `worker_manager` and asserts worker PID reuse. |
| `tests/integration/test_stardist_adapter_e2e.py` | `src/bioimage_mcp/api/execution.py` | execute_step | ✓ VERIFIED | Imports and calls `execute_step` twice. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|------------|--------|----------------|
| (None mapped to Phase 16) | N/A | N/A |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

### Human Verification Required

1. **Install StarDist env from lockfile**
   - **Test:** `conda-lock install -n bioimage-mcp-stardist envs/bioimage-mcp-stardist.lock.yml`
   - **Expected:** Environment installs without solver errors.
   - **Why human:** Requires conda/micromamba and network access.

2. **Run StarDist meta.list**
   - **Test:** Execute `bioimage_mcp_stardist/entrypoint.py` in the stardist env and send `meta.list`.
   - **Expected:** Functions list includes `StarDist2D.from_pretrained` and `StarDist2D.predict_instances`.
   - **Why human:** Requires runtime execution inside isolated env.

3. **Run StarDist meta.describe**
   - **Test:** Send `meta.describe` for `stardist.models.StarDist2D.predict_instances`.
   - **Expected:** `params_schema`, `tool_version`, and `introspection_source` returned.
   - **Why human:** Requires runtime introspection in isolated env.

4. **Execute StarDist workflow**
   - **Test:** `from_pretrained` -> `predict_instances` with a small test image.
   - **Expected:** Returns ObjectRef, then LabelImageRef (OME-Zarr) + details JSON.
   - **Why human:** Requires StarDist/TensorFlow runtime and model download.

5. **Run StarDist tests**
   - **Test:** `pytest tests/contract/test_stardist_* -v` and `pytest tests/integration/test_stardist_adapter_e2e.py -v` (env installed).
   - **Expected:** Contract tests pass; integration test passes when env available.
   - **Why human:** Requires test execution in correct environments.

### Gaps Summary

Automated verification confirms the StarDist env files, tool pack scaffold, discovery adapter, execution wiring, tests, and docs are present and substantive. Goal achievement still requires runtime validation inside the StarDist conda environment (meta.list/meta.describe and inference execution), which must be performed by a human operator.

---

_Verified: 2026-02-01T21:20:00Z_
_Verifier: Claude (gsd-verifier)_
