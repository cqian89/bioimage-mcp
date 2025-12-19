# Code Review: 001-cellpose-pipeline

Date/Time: 2025-12-19T15:24:25+01:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | Spec tasks marked complete, but key deliverables missing: dynamic schema enrichment via `meta.describe` not wired into `describe_function`; `datasets/README.md` missing; `datasets/samples/` empty (no sample images). |
| Tests | PASS | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.../src pytest -p no:cacheprovider`: **240 passed, 1 skipped, 2 xfailed**. Without `PYTHONPATH` (or editable install), `tests/unit/test_imports.py::test_main_module_invocation` fails in subprocess with `No module named bioimage_mcp`. |
| Coverage | LOW | Many “integration/e2e” tests monkeypatch tool execution (`execute_step`) and skip validation, so they do not cover live image loading, real segmentation, subprocess JSON protocol, or env isolation. |
| Architecture | FAIL | Plan/spec call for on-demand schema enrichment via `meta.describe` (cached in SQLite). Current implementation only serves the static manifest `params_schema`; `schema_cache` exists but is unused. |
| Constitution | FAIL | Violations/risks against Principle I (on-demand full schemas via `describe_function`) and Principle II (isolated tool execution) due to missing schema enrichment + permissive env fallback. |

## Scope / Notes
- FEATURE_DIR: `specs/001-cellpose-pipeline/`
- Repo working tree appeared clean (`git status --porcelain` had no changes).
- Review constraint: analysis-only; no code changes made.

## Findings

### CRITICAL
1. **Dynamic schema enrichment not implemented (meta.describe not used by describe_function)**
   - `specs/001-cellpose-pipeline/plan.md` + `specs/001-cellpose-pipeline/tasks.md` specify on-demand schema enrichment (fetch via tool `meta.describe` when `describe_function` is called; cache in SQLite).
   - Current behavior:
     - `src/bioimage_mcp/bootstrap/serve.py` upserts `params_schema` directly from manifests.
     - `src/bioimage_mcp/api/discovery.py` `describe_function()` returns what’s already in SQLite (no enrichment).
     - `src/bioimage_mcp/storage/sqlite.py` defines `schema_cache`, and `src/bioimage_mcp/registry/index.py` implements cache methods, but nothing calls them.
   - Result: `tools/cellpose/manifest.yaml` intentionally ships an empty/minimal schema, so `describe_function("cellpose.segment")` cannot return the intended parameter schema.

2. **“Integration/E2E” tests are mostly mocked and do not test live tool behavior**
   - Examples:
     - `tests/integration/test_cellpose_e2e.py` monkeypatches `bioimage_mcp.api.execution.execute_step` and even creates a fake TIFF header.
     - `tests/integration/test_validate_pipeline.py` monkeypatches `execute_step` and uses placeholder URIs.
     - `tests/integration/test_mcp_llm_simulation.py` uses real dataset paths but still monkeypatches `execute_step` and sets `skip_validation=True`.
   - This leaves large blind spots:
     - JSON stdin/stdout tool protocol (`src/bioimage_mcp/runtimes/executor.py`) correctness under real tool output.
     - Env isolation path (`micromamba run -n ...`) correctness.
     - Real image parsing and label writing paths (`tifffile`, `bioio` metadata extraction).
     - Real Cellpose API behavior and output file naming.

3. **Sample data + license documentation task is incomplete**
   - `specs/001-cellpose-pipeline/tasks.md` includes:
     - T033: add 1–2 sample microscopy images to `datasets/samples/`
     - T036: document sources/licenses in `datasets/README.md`
   - Current state:
     - `datasets/samples/` exists but is empty.
     - `datasets/README.md` is missing.
     - `scripts/validate_pipeline.py` defaults to `datasets/samples/` and returns non-zero in non-`--dry-run` mode if no images are present.

### HIGH
1. **Workflow record persistence mismatch**
   - `runs` table has `native_output_ref_id` (`src/bioimage_mcp/storage/sqlite.py`), and `Run` model exposes `native_output_ref_id` (`src/bioimage_mcp/runs/models.py`).
   - `ExecutionService.run_workflow()` generates a workflow record and returns `workflow_record_ref_id`, but `RunStore` does not persist `native_output_ref_id` in the DB (neither `create_run()` nor `set_status()` updates it).
   - Result: replay linkage relies on the returned value/outputs, not durable run state.

2. **Work directory not run-isolated**
   - `ExecutionService.run_workflow()` uses `artifact_store_root/work/runs` as a shared directory.
   - Concurrency / repeated runs can collide on filenames like `labels.ome.tiff` and `cellpose_seg.npy`.

3. **Test runner environment mismatch for subprocess import**
   - `tests/unit/test_imports.py` runs `python -m bioimage_mcp --help` without ensuring `PYTHONPATH=src` (or editable install).
   - In this environment, `pytest` fails unless `PYTHONPATH` is explicitly set (or the package is installed).

4. **Cellpose version intent mismatch**
   - `envs/bioimage-mcp-cellpose.yaml` pins `cellpose>=3.0,<4.0`.
   - `specs/001-cellpose-pipeline/tasks.md` references Cellpose v4 API changes (e.g., “Cellpose which is removed in v4”).
   - Tool implementation uses `cellpose.models.CellposeModel` (`tools/cellpose/bioimage_mcp_cellpose/ops/segment.py`), but the version mismatch increases risk of API drift and should be reconciled explicitly.

### MEDIUM
1. **Pytest warnings from tests returning values**
   - `tests/integration/test_mcp_llm_simulation.py` returns values from test functions, triggering `PytestReturnNotNoneWarning`.
   - This can be promoted to an error in stricter CI settings.

2. **`.gitignore` ignores `*.npy` globally**
   - This is likely intended to avoid committing Cellpose bundles/caches, but it may unintentionally ignore future legitimate `.npy` fixtures or outputs outside Cellpose.

## Remediation / Suggestions

### Address the user concern: reduce reliance on mocks
- Keep mocks for unit tests (fast, deterministic), but add at least **one** truly “live” path test that covers the tool protocol + real image I/O.
- Recommended structure:
  - Mark live tests with `@pytest.mark.pipeline_validation` and/or a new marker like `@pytest.mark.live_tool`.
  - Gate on availability:
    - `pytest.importorskip("cellpose")` (for running in-process) and/or check presence of `micromamba` if testing env isolation.
    - Optional env var gate: `BIOIMAGE_MCP_RUN_LIVE=1`.
  - Use a tiny synthetic TIFF (e.g., 32×32 or 64×64) written via `tifffile` to avoid licensing and large binaries.
  - Do **not** monkeypatch `execute_step`; let it execute `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py` end-to-end.

### Implement the planned schema enrichment path
- Move the “call `meta.describe` on-demand” behavior into the server-side `describe_function` flow (likely `src/bioimage_mcp/api/discovery.py`) or a dedicated registry layer.
- Use the existing `schema_cache` table (`src/bioimage_mcp/storage/sqlite.py`) + cache helpers (`src/bioimage_mcp/registry/index.py`).
- Add a test that fails if `describe_function("cellpose.segment")` returns the empty manifest schema.
  - If Cellpose is too heavy, use a lightweight test toolpack (like `tests/integration/test_run_workflow_e2e.py` does) that implements `meta.describe` and prove the server enriches + caches.

### Make validation real (or rename it)
- If the goal is genuine pipeline validation (FR-010), ensure `datasets/samples/` contains at least one small image and add `datasets/README.md` with license/source.
- Alternatively, if sample data cannot be vendored, adjust validation to use a generated synthetic sample and document it.

### Fix the subprocess import test setup
- Decide on one supported test mode:
  - **Editable install** in CI (`pip install -e .`) and keep the subprocess test as-is; or
  - Make the subprocess test set `PYTHONPATH=src` explicitly.

---

## Addendum: Dataset + Dynamic Discovery Notes

### Proposal: Use `datasets/FLUTE_FLIM_data_tif/` as the test dataset
You already have a real dataset in-repo at `datasets/FLUTE_FLIM_data_tif/` (TCSPC FLIM TIFFs). This is a better default than the currently-empty `datasets/samples/` directory.

Recommended changes (conceptual):
- Treat `datasets/FLUTE_FLIM_data_tif/` as the canonical “bundled test dataset” for `pipeline_validation`.
- Update `scripts/validate_pipeline.py` default `--samples-dir` to point to `datasets/FLUTE_FLIM_data_tif/` (or rename the flag to `--datasets-dir` and default to that path).
- Update any tests/scripts that currently fabricate placeholder TIFFs to instead select a real file from this directory (e.g., `hMSC-ZOOM.tif` or “smallest file by size” selection as done in `tests/integration/test_mcp_llm_simulation.py`).

Important caveats (still need addressing):
- **License/provenance**: even if the files are already in the repo, `datasets/README.md` should document their origin/license, otherwise the “sample dataset” requirement remains partially unsatisfied.
- **Semantics**: these are **FLIM** files (likely multi-dimensional: time bins / channels). The current v0.1 segmentation step (`tifffile.imread(...)` → `CellposeModel.eval(...)`) assumes an intensity image. Using raw FLIM arrays may be unstable or meaningless unless you define a deterministic conversion (e.g., sum/mean over lifetime bins, select a channel, or max-project a dimension). If you adopt FLUTE as the default validation dataset, you should also decide and document what “preprocessing” means for these files.

### Why tool/function querying feels “not dynamic” today
There are two separate “dynamic” axes:
1. **Tool/function catalog**: currently populated from YAML manifests at server startup (`src/bioimage_mcp/bootstrap/serve.py` loads manifests and upserts into SQLite). If you add/modify manifests while the server is running, discovery won’t see them until restart (no refresh mechanism).
2. **Dynamic parameter schemas**: the spec requires `describe_function(fn_id)` to call `meta.describe` on-demand and cache results. This is the bigger gap: although `meta.describe` handlers exist (e.g., built-ins in `tools/builtin/bioimage_mcp_builtin/entrypoint.py`), the core server never calls them, so schemas remain whatever the manifest seeded.

The “gaussian smoothing” observation maps to this: `tools/builtin/manifest.yaml` has a partial schema for `builtin.gaussian_blur`, and `bioimage_mcp_builtin/entrypoint.py` implements `meta.describe`, but nothing wires `DiscoveryService.describe_function()` to invoke it.

### Proposed implementation approach: on-demand schema enrichment via `meta.describe`
The minimal, spec-aligned approach is:
- Keep `list_tools` and `search_functions` backed by SQLite (summary-first, paginated).
- Implement **on-demand enrichment** in the `describe_function(fn_id)` path:
  1. Look up the function row.
  2. If `params_schema` is empty/minimal (or `introspection_source` is missing), resolve which tool pack owns it.
  3. Load the owning manifest from disk (using the `manifest_path` already stored in the `tools` table) to retrieve `entrypoint`, `env_id`, and confirm `meta.describe` exists.
  4. Call `meta.describe` through the normal subprocess boundary (`src/bioimage_mcp/runtimes/executor.py::execute_tool`) with `{"fn_id": "meta.describe", "params": {"target_fn": fn_id}}`.
  5. Validate response shape (reuse `tests/contract/test_meta_describe_contract.py` expectations).
  6. Cache the schema in `schema_cache` keyed by `(tool_id, tool_version, fn_id)` and also upsert the enriched schema into the `functions` table for faster subsequent reads.

Key details / pitfalls to plan for:
- `RegistryIndex.get_function()` currently does not return `tool_id`, so `describe_function()` can’t locate the manifest/tool without either (a) widening that query to include `tool_id` or (b) adding a separate lookup method (`fn_id → tool_id`).
- Avoid doing this enrichment during `list_tools` / `search_functions` to preserve Principle I (no schema blobs in listings) and to keep discovery fast.
- The existing `schema_cache` table and helper methods in `src/bioimage_mcp/registry/index.py` are a good starting point, but they’re currently unused.

### What “dynamic” should look like for built-ins (gaussian blur)
- Once on-demand enrichment is implemented, `describe_function("builtin.gaussian_blur")` should return the richer schema from `meta.describe` (including curated descriptions).
- Today the built-in `meta.describe` implementation mostly emits descriptions/defaults and may omit JSON Schema `type` fields; you likely want it to reuse the shared introspection utility (`src/bioimage_mcp/runtimes/introspect.py::introspect_python_api`) so that types/defaults/required are consistent across tool packs.

### Test strategy for dynamic enrichment (without making CI brittle)
- Add a small integration test that uses a lightweight “test tool pack” which implements `meta.describe` and returns a known schema. Assert:
  - first `describe_function()` triggers a tool invocation and populates cache
  - second `describe_function()` is served from cache and does not re-invoke the tool
- Separately, add a built-in test asserting `describe_function("builtin.gaussian_blur")` includes the enriched description text once wiring exists.

