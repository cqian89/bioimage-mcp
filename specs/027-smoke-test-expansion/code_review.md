# Code Review Notes

## 2026-01-22T08:17:33+01:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | `specs/027-smoke-test-expansion/tasks.md` marks all tasks complete, but `tests/smoke/test_equivalence_phasorpy.py` fails and `tests/smoke/test_smoke_markers.py` errors under `-m smoke_minimal`. |
| Tests | FAIL | Unit tests: 22 passed. Smoke tests: 1 passed, 1 failed. Marker enforcement test: error due to async fixture usage. |
| Coverage | LOW | Core deliverable is smoke-suite coverage; currently a key equivalence test and a smoke_minimal gate test do not execute cleanly. |
| Architecture | FAIL | `specs/027-smoke-test-expansion/plan.md` states "no MCP API changes", but `src/bioimage_mcp/api/server.py` exposes a new `verbosity` parameter and applies `RunResponseSerializer` in `src/bioimage_mcp/api/serializers.py`. |
| Constitution | PASS | No new MCP tools added; serializer changes generally reduce token bloat and keep artifact references bounded. Watch for unintended schema/behavior drift. |

### Findings

- **CRITICAL**: PhasorPy equivalence test fails.
  - `tests/smoke/test_equivalence_phasorpy.py` fails with `Invalid parameter: not enough samples=1 along axis=0`.
  - Tool log: `/home/qianchen/.bioimage-mcp/artifacts/objects/7b8c2d92fa1945aaa029adf41e72fd2b.log`.
  - Likely cause: `axis` computed from BioImage metadata does not match the actual array rank/order provided to `phasorpy.phasor.phasor_from_signal` inside the tool runtime (singleton axes/TCZYX expansion shifting the intended axis).

- **CRITICAL**: `smoke_minimal` marker enforcement test errors due to async fixture wiring.
  - `pytest tests/smoke/test_smoke_markers.py -m smoke_minimal` errors because `tests/smoke/conftest.py` has an autouse sync fixture (`interaction_logger`) depending on the async fixture `live_server`.
  - This blocks running any sync smoke_minimal tests that trigger the autouse fixture.

- **HIGH**: Plan/spec drift risk from MCP `run` response changes.
  - `src/bioimage_mcp/api/server.py` now always serializes run results through `RunResponseSerializer` (and accepts a new `verbosity` arg).
  - This is likely beneficial for token safety, but it contradicts `specs/027-smoke-test-expansion/plan.md` (“no MCP API changes”) and may affect downstream clients expecting prior fields.

- **MEDIUM**: Pandas equivalence test relies on somewhat brittle I/O conventions.
  - `tests/smoke/test_equivalence_pandas.py` passes inputs using the key `image` (for table/df refs) and includes a fallback attempt; this suggests possible schema/input-name mismatch or inconsistent tool input naming.
  - Test writes temporary exports into `~/.bioimage-mcp/artifacts` via `base.io.table.export`; if allowlists differ in CI, this could become flaky.

- **LOW**: Deprecation warnings in pandas GroupBy metadata extraction.
  - `src/bioimage_mcp/registry/dynamic/adapters/pandas.py` uses `DataFrameGroupBy.grouper`, which emits `FutureWarning` in current pandas.

### Tests Executed

- `pytest tests/unit/api/test_run_response_serializer.py tests/unit/ops/test_table_export.py tests/unit/registry/test_pandas_chaining.py tests/unit/registry/test_pandas_groupby.py`
  - Result: `22 passed` (with pandas `FutureWarning`s).
- `pytest tests/smoke/test_equivalence_pandas.py tests/smoke/test_equivalence_phasorpy.py -m smoke_full`
  - Result: `1 passed, 1 failed` (PhasorPy failed).
- `pytest tests/smoke/test_smoke_markers.py -m smoke_minimal`
  - Result: error (async fixture requested by sync autouse fixture).

### Remediation / Suggestions

1. Fix PhasorPy axis handling so the test is stable.
   - Prefer mapping `axis` by dimension name (e.g., choose the axis corresponding to the "C"/phase dimension) rather than searching for `size==16` in native metadata.
   - Alternatively, update the PhasorPy adapter (`src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`) to interpret `axis` relative to the provided artifact's native `dims`/`shape`, and translate to the runtime array's actual axis after any expansion.

2. Make `smoke_minimal` tests runnable without AnyIO/async handling.
   - In `tests/smoke/conftest.py`, avoid having a sync autouse fixture depend on async fixtures.
   - Options:
     - Convert `interaction_logger` to an async fixture (`async def ...`) and keep it compatible with `@pytest.mark.anyio` tests.
     - Or remove the `live_server` dependency from the autouse fixture when `--smoke-record` is not enabled.
     - Or mark marker-enforcement tests to run under AnyIO and make them async (least preferred; these tests shouldn't need a server).

3. Reconcile implementation with `specs/027-smoke-test-expansion/plan.md`.
   - `verbosity` and `RunResponseSerializer` are intentional. update the plan/spec and project docs to explicitly describe this MCP surface change.

