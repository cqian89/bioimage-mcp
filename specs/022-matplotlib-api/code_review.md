# Code Review: 022-matplotlib-api

## Review Log

### 2026-01-13T09:05:32+01:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | Core feature is implemented, but `tests/integration/test_matplotlib_memory_leak.py` and `tests/integration/test_matplotlib_session_replay.py` are currently untracked (`git status` shows `??`), and a few task-level requirements appear partially met (see Findings). |
| Tests    | PASS | All executed tests passed (unit, contract, and a broad set of integration tests). Some deprecation/future warnings observed. |
| Coverage | HIGH | Strong coverage across unit/contract/integration, including US1–US8 workflows + replay/leak tests; remaining gaps are mainly security/validation edge cases. |
| Architecture | PASS | Matches `specs/022-matplotlib-api/plan.md` design: dynamic source in `tools/base/manifest.yaml`, adapter-based discovery/dispatch, Agg headless backend, artifact refs for outputs. |
| Constitution | FAIL | **CRITICAL**: current Matplotlib allowlist + execution path can bypass filesystem allowlists (Constitution V) via file I/O-capable functions and unvalidated params. |

#### What I Reviewed

- Feature docs: `specs/022-matplotlib-api/tasks.md`, `specs/022-matplotlib-api/plan.md`
- Core changes (high level):
  - `src/bioimage_mcp/registry/dynamic/adapters/matplotlib.py`
  - `src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py`
  - `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
  - `src/bioimage_mcp/artifacts/models.py`
  - `tools/base/manifest.yaml`
- Representative tests executed:
  - `pytest -p no:cacheprovider tests/unit/artifacts/test_matplotlib_refs.py`
  - `pytest -p no:cacheprovider tests/unit/registry/test_matplotlib_adapter.py`
  - `pytest -p no:cacheprovider tests/contract/test_matplotlib_env.py`
  - `pytest -p no:cacheprovider tests/contract/test_matplotlib_adapter_discovery.py`
  - `pytest -p no:cacheprovider tests/integration/test_us1_histograms.py`
  - `pytest -p no:cacheprovider tests/integration/test_us2_roi_overlays.py`
  - `pytest -p no:cacheprovider tests/integration/test_us3_subplots.py`
  - `pytest -p no:cacheprovider tests/integration/test_us4_scatter_plots.py`
  - `pytest -p no:cacheprovider tests/integration/test_us5_time_series.py`
  - `pytest -p no:cacheprovider tests/integration/test_us6_export.py`
  - `pytest -p no:cacheprovider tests/integration/test_us7_stats_plots.py`
  - `pytest -p no:cacheprovider tests/integration/test_us8_z_profiles.py`
  - `pytest -p no:cacheprovider tests/integration/test_matplotlib_axes_features.py`
  - `pytest -p no:cacheprovider tests/integration/test_matplotlib_memory_leak.py`
  - `pytest -p no:cacheprovider tests/integration/test_matplotlib_session_replay.py`
  - `pytest -p no:cacheprovider tests/integration/test_pandas_pipeline.py`
  - `pytest -p no:cacheprovider tests/integration/test_performance.py`

#### Findings

- **CRITICAL**: Filesystem allowlist bypass via Matplotlib API surface.
  - `src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py` includes pyplot functions that can read/write arbitrary paths (e.g., `imread`, `imsave`).
  - `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py` executes many pyplot/object methods via `pyplot_op()` / `generic_op()` with `**params` pass-through and no `fs_allowlist_*` enforcement.
  - The core server appears not to enforce JSON-schema validation of params for dynamic functions, so callers may provide parameters not present in the discovery schema (increasing the risk surface).
  - This conflicts with Constitution V (“File and network access policies MUST be explicit and verifiable through allowlists”).

- **HIGH**: Session isolation of `obj://` artifacts is weak.
  - Matplotlib object URIs are minted as `obj://default/matplotlib/<uuid>` (no session scoping).
  - Tool-side object lookup is by URI only (`OBJECT_CACHE`), so a client that can guess/obtain a URI could potentially reference objects across sessions.

- **MEDIUM**: `AxesImageRef` exists but `imshow` returns `ObjectRef`.
  - `src/bioimage_mcp/artifacts/models.py` defines `AxesImageRef`, but `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py:imshow()` returns type `ObjectRef`.
  - This reduces schema fidelity and undercuts the purpose of the more specific artifact types.

- **MEDIUM**: Tasks marked done vs repo state.
  - `tests/integration/test_matplotlib_memory_leak.py` and `tests/integration/test_matplotlib_session_replay.py` exist and pass, but are untracked (`git status` shows `??`).
  - `specs/022-matplotlib-api/tasks.md` marks these tasks as completed.

- **MEDIUM**: Memory leak stress test strength vs task text.
  - `specs/022-matplotlib-api/tasks.md` calls for generating 100+ figures; `tests/integration/test_matplotlib_memory_leak.py` currently loops 10 times.

- **LOW**: Test warnings.
  - Pandas `FutureWarning` about `DataFrameGroupBy.grouper` deprecation.
  - Matplotlib `UserWarning` about redundant marker.
  - `bioio_ome_tiff` deprecation warning about ignored parser argument.

#### Remediation / Suggestions

- **Close the CRITICAL allowlist bypass** (recommended priority).
  - Remove pyplot I/O helpers from the allowlist (`imread`, `imsave`, and any similar file-touching APIs) unless they are wrapped with explicit path validation.
  - Add a guardrail in Matplotlib dispatch that rejects any param that looks like a filesystem path unless it is validated against `BIOIMAGE_MCP_FS_ALLOWLIST_READ/WRITE` (mirroring `tools/base/bioimage_mcp_base/ops/io.py` behavior).
  - Consider enforcing param schema validation for dynamic functions in the core execution path (reject unknown keys) so “hidden” parameters can’t be passed through.

- **Strengthen session isolation for `obj://` references**.
  - Include `session_id` and `env_id` in the minted URI (or enforce ownership checks at lookup time).
  - Alternatively, refuse to resolve `obj://` unless the ref_id is registered to the active session in the core memory store.

- **Align `imshow` output type**.
  - Return `AxesImageRef` (with required metadata like `parent_axes_ref_id`, `origin`, `cmap`) instead of generic `ObjectRef`.
  - Update I/O pattern mapping and discovery hints accordingly, so `describe()` reflects the richer artifact types.

- **Make repo state match `tasks.md`**.
  - Add the two new integration tests to git (or mark the corresponding tasks as incomplete until they’re tracked).

- **Reconcile stress test intent**.
  - If CI/runtime constraints require a smaller loop than 100+, document the rationale and/or add a separate slow-marked test for the 100+ case.
