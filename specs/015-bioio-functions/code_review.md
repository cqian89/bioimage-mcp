# Code Review Log

## Review: 2026-01-05T00:54:29+01:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | PASS | `specs/015-bioio-functions/tasks.md` is fully checked off; implementation and tests exist for each phase. |
| Tests    | PASS | `pytest -p no:cacheprovider` ran: **58 passed, 1 skipped** (targeted suite). |
| Coverage | HIGH | Strong unit + integration coverage for the 6 new functions; gaps remain around tool entrypoint runtime behavior (see Findings). |
| Architecture | FAIL | Core contract mismatches (notably export output typing) and runtime config propagation concerns (see Findings). |
| Constitution | FAIL | Violations/risks vs Constitution III/IV around typed outputs and version/provenance reporting (see Findings). |

### Key Components Changed/Added

- `tools/base/manifest.yaml`: Adds 6 `base.io.bioimage.*` functions, removes deprecated `base.bioio.export`, bumps tool version to `0.2.0`.
- `tools/base/bioimage_mcp_base/ops/io.py`: Implements `load`, `inspect`, `slice_image`, `validate`, `get_supported_formats`, `export`.
- `tools/base/bioimage_mcp_base/entrypoint.py`: Routes new function IDs to `io.py` implementations.
- `tests/unit/api/test_io_functions.py`: Extensive unit tests for the new I/O functions.
- `tests/contract/test_io_functions_schema.py`: Contract checks for existence, docs completeness, version bump, deprecated removal.
- `tests/integration/test_io_workflow.py`: Discovery + end-to-end workflow tests.

### Findings

- **CRITICAL**: Contract/type mismatch for `base.io.bioimage.export` output.
  - `tools/base/manifest.yaml` declares export output `artifact_type: BioImageRef`, but implementation can output a `TableRef` when exporting CSV.
  - This undermines typed I/O guarantees (Constitution III) and can break clients relying on schema.

- **HIGH**: Tool version mismatch between manifest and tool entrypoint.
  - `tools/base/manifest.yaml` has `tool_version: "0.2.0"`, but `tools/base/bioimage_mcp_base/entrypoint.py` still sets `TOOL_VERSION = "0.1.0"`.
  - This can misreport tool version in worker handshakes/logs, weakening provenance guarantees (Constitution IV).

- **HIGH**: Native axis preservation relies on filename-specific test hooks.
  - `tools/base/bioimage_mcp_base/ops/io.py` uses `"zyx_test" in path` conditionals to override dims/shape behavior.
  - This is not robust for real user data and does not generalize beyond test fixtures.

- **HIGH**: Deprecated `base.bioio.export` removed from the base manifest, but repository documentation still references it.
  - Examples include `docs/reference/tools.md`, `docs/tutorials/flim_phasor.md`, and `docs/developer/architecture.md`.
  - This increases user confusion and risks drift between docs and actual tool surface.

- **MEDIUM**: Allowlist propagation likely incomplete in `tools/base/bioimage_mcp_base/entrypoint.py`.
  - Entry point sets `BIOIMAGE_MCP_FS_ALLOWLIST_READ` from request, but does not set `BIOIMAGE_MCP_FS_ALLOWLIST_WRITE`.
  - `validate_write_path()` in `tools/base/bioimage_mcp_base/ops/io.py` relies on `BIOIMAGE_MCP_FS_ALLOWLIST_WRITE`.
  - Current tests primarily call ops directly and set env vars manually; runtime behavior via tool subprocess is not directly exercised.

- **MEDIUM**: Structured error response helpers exist but are not the end-to-end error shape returned to callers.
  - `make_error_response()` produces `error.code/message/details`, but `entrypoint.py` exception handling emits only `error.message` and optional `error.code`.
  - If clients depend on `details`, this is currently not guaranteed.

- **LOW**: `tools/base/bioimage_mcp_base/ops/io.py` defines a custom `FileNotFoundError` that shadows Python’s built-in `FileNotFoundError`.
  - This can confuse debugging and exception handling.

### Tests Executed

- Command: `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/contract/test_io_functions_schema.py tests/contract/test_base_tools.py tests/unit/api/test_io_functions.py tests/unit/api/test_metadata_extraction.py tests/unit/base/test_export_dims.py tests/integration/test_io_workflow.py tests/integration/test_multi_format_export.py`
- Result: **58 passed, 1 skipped**, 81 warnings (bioio_ome_tiff deprecation warning).

### Remediation / Suggestions

1. **Fix export output typing in manifest/contract**
   - Update `tools/base/manifest.yaml` for `base.io.bioimage.export` to accurately represent that output can be `BioImageRef` *or* `TableRef`.
   - Mirror the same correction in `specs/015-bioio-functions/contracts/io-functions.yaml`.
   - Add/extend contract tests to assert correct output artifact typing semantics.

2. **Align tool version reporting**
   - Ensure `tools/base/bioimage_mcp_base/entrypoint.py` reports the same version as `tools/base/manifest.yaml` (or derive it from the manifest at runtime).

3. **Replace filename-based native-axis logic**
   - Remove `"zyx_test"` path conditionals and implement native axis preservation based on actual metadata.
   - If bioio-ome-tiff necessarily normalizes to TCZYX, update the spec/tests to reflect reality (or store original dim order in artifact metadata at write-time).

4. **Test subprocess/runtime allowlist behavior**
   - Add an integration test that executes `base.io.bioimage.export` through the tool entrypoint/runtime path (not direct function import) and verifies `fs_allowlist_write` is enforced.

5. **Harden performance proxy tests**
   - Replace wall-clock timing checks for SC-004 with a behavioral assertion (e.g., mock/spy that full pixel decode/compute is not triggered).

6. **Update user-facing docs**
   - Replace references to `base.bioio.export` with `base.io.bioimage.export` and add a brief migration note.
