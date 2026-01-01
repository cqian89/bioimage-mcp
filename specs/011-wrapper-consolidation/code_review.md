
## Code Review - 2026-01-01T00:37:50+00:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | Several tasks marked complete are only simulated (persistent workers, mem artifacts) and the 5D Gaussian blur acceptance test is XFAIL. |
| Tests | PASS | Targeted contract/unit/integration suites passed; 1 expected XFAIL in axis-independent Gaussian blur (5D) case. |
| Coverage | LOW | No coverage metric collected; gaps around real persistent workers and true mem data lifecycle. |
| Architecture | FAIL | Cross-env handoff and mem artifacts are implemented as core-side materialization + simulated memory, diverging from plan.md/spec.md. |
| Constitution | FAIL | Core performs export/materialization and uses tifffile fallbacks; violates Constitution III/II expectations. |

### Tests Run
- PYTHONDONTWRITEBYTECODE=1 pytest -q -o cache_dir=/tmp/pytest_cache --basetemp=/tmp/pytest_basetemp tests/contract/test_memory_artifact_schema.py tests/contract/test_axis_tools_schema.py tests/unit/registry/test_xarray_adapter.py
- PYTHONDONTWRITEBYTECODE=1 pytest -q -o cache_dir=/tmp/pytest_cache --basetemp=/tmp/pytest_basetemp tests/integration/test_axis_independent_processing.py tests/integration/test_worker_resilience.py tests/integration/test_cross_env_handoff.py tests/integration/test_artifact_export.py tests/integration/test_axis_manipulation.py tests/integration/test_provenance_chain.py

### Findings
- CRITICAL: mem artifacts are simulated via _simulated_path and still backed by files, not worker memory (src/bioimage_mcp/api/execution.py, output_mode == "memory").
- CRITICAL: Persistent workers are not actually persistent; PersistentWorkerManager explicitly defers process reuse (src/bioimage_mcp/runtimes/persistent.py). Conflicts with Spec 011 requirements and tasks T008/T016/T045.
- CRITICAL: Core-side materialization uses tifffile.imwrite during automatic handoff (src/bioimage_mcp/api/execution.py), and adapters also fall back to tifffile (src/bioimage_mcp/registry/dynamic/adapters/xarray.py). Conflicts with Constitution III and project I/O guidance to use bioio writers.
- HIGH: Cross-env handoff is performed inside ExecutionService.run_workflow (core) instead of delegating export/import to tool environments, diverging from specs/011-wrapper-consolidation/plan.md and Constitution III (source-env export, target-env import).
- HIGH: tests/integration/test_axis_independent_processing.py has an XFAIL for gaussian_blur_5d_produces_mem_artifact: skimage adapter incorrectly reorders 5D axes on output.
- MEDIUM: XarrayAdapterForRegistry pads missing dimensions by prefixing letters, which can yield nonstandard axis orders for <5D results (src/bioimage_mcp/registry/dynamic/adapters/xarray.py).
- LOW: tasks.md references tools/base/pyproject.toml cleanup (T039), but no such file is tracked; task wording likely needs correction.

### Remediation / Suggestions
1. Implement true per-session, per-env persistent worker subprocesses and store actual in-memory objects keyed by mem:// URI; remove _simulated_path once real memory storage exists.
2. Move cross-env materialization out of core: core should orchestrate base.bioio.export (or equivalent) in the source environment, then import in the target environment, matching Constitution III and plan.md.
3. Replace tifffile usage in core paths with bioio.writers.OmeTiffWriter.save (or other bioio writers) to preserve OME metadata and avoid format drift.
4. Fix the skimage adapter 5D axis reorder bug, then remove the XFAIL and add regression coverage for 5D + 2D Gaussian blur outputs.
5. Add targeted tests for worker crash + mem invalidation with real process persistence (currently only metadata invalidation is exercised).

