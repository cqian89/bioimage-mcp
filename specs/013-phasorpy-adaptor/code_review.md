## Code Review (2026-01-03T06:41:42.000784Z)

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | Several `[X]` tasks diverge from described implementation locations; PlotRef end-to-end currently crashes the worker. |
| Tests | FAIL | `pytest tests/contract/test_phasorpy_discovery.py ...` passed; `pytest tests/integration/test_flim_phasor_e2e.py` failed. |
| Coverage | LOW | No end-to-end test covers `base.phasorpy.plot.plot_phasor`; several task tests are “happy-path only” or contain outdated expectations. |
| Architecture | FAIL | PlotRef/plot dispatch path is not JSON-serializable and does not integrate with artifact import flow; reader selection is too strict for FLUTE TIFFs labeled as OME-TIFF. |
| Constitution | FAIL | PlotRef workflow violates Artifact Reference + Observability expectations (worker crash; output not importable/persisted for `get_artifact`). |

### Findings

- **CRITICAL**: `base.phasorpy.plot.plot_phasor` crashes the base tool worker (no NDJSON response).
  - Evidence: Running a minimal `ExecutionService` workflow (with `skip_validation=True`) fails with `Worker closed stdout without response`.
  - Likely cause: `tools/base/bioimage_mcp_base/entrypoint.py` serializes responses via `json.dumps(response)` without a `default=` encoder, but `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py` returns a `PlotRef` Pydantic object (not JSON-serializable) via `tools/base/bioimage_mcp_base/dynamic_dispatch.py`.
  - Impact: Breaks US2 (PlotRef) and SC-004 (plot artifacts accessible).

- **CRITICAL**: `tests/integration/test_flim_phasor_e2e.py` fails due to TIFF reader selection.
  - Failure: BioImage cannot read `datasets/FLUTE_FLIM_data_tif/Fluorescein_Embryo.tif` when the input is declared as `format: OME-TIFF`.
  - Error excerpt: `bioio-ome-tiff ... Unknown property ... AnnotationRef`.
  - Likely cause: `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py:_load_image` forces the OME-TIFF reader when `format == "OME-TIFF"`, preventing fallback to other readers (e.g. Bio-Formats) for TIFFs that are not valid OME-TIFF.

- **HIGH**: PlotRef artifacts are not integrated with the server’s artifact import/persistence flow.
  - Server imports outputs only when tool responses provide `path` (see `src/bioimage_mcp/api/execution.py` output import loop). The current PlotRef model uses `uri` (and `write_plot()` returns a `PlotRef` object) rather than a `{type, format, path, metadata}` dict.
  - This blocks `get_artifact(ref_id)` because the artifact store indexes by `ref_id`.

- **MEDIUM**: Task/spec/test mismatches reduce confidence in “all tasks completed”.
  - `specs/013-phasorpy-adaptor/tasks.md` marks tuple-return handling as implemented in `src/bioimage_mcp/registry/dynamic/introspection.py` (T014), but that file does not implement tuple-return mapping; tuple handling lives in `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`.
  - `specs/013-phasorpy-adaptor/tasks.md` claims matplotlib capture + `write_plot()` connection in `tools/base/bioimage_mcp_base/dynamic_dispatch.py` (T020/T022), but current capture logic is in `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`.

- **MEDIUM**: Allowlist enforcement (T041) is only tested positively in `tests/integration/test_phasorpy_workflow.py`; the “negative” path (deny outside allowlist) is not covered there.

- **LOW**: Some tests contain outdated “expected to fail” comments (e.g., `tests/contract/test_phasorpy_discovery.py`, `tests/integration/test_phasorpy_workflow.py`), which makes the suite harder to interpret.

### Tests Run

- Passed: `pytest -q -p no:cacheprovider tests/contract/test_phasorpy_discovery.py tests/contract/test_plotref_artifact.py tests/contract/test_phasor_metadata.py`
- Failed: `pytest -q -p no:cacheprovider tests/integration/test_flim_phasor_e2e.py`
- Passed (selected): `pytest -q -p no:cacheprovider tests/integration/test_phasorpy_workflow.py -k "sdt_loading_normalization or ptu_loading_normalization or lif_loading_normalization or plot_phasor"`

### Remediation / Suggestions

1. Fix PlotRef execution path to return JSON-serializable tool outputs.
   - Prefer returning a plain dict from the tool process: `{type: "PlotRef", format: "PNG", path: ".../plot.png", metadata: {...}}` so `ExecutionService` can import it into the artifact store.
   - Alternatively, teach `tools/base/bioimage_mcp_base/dynamic_dispatch.py` to convert Pydantic models via `model_dump()` before returning, but the output still needs a `path` for server import.
   - Add an end-to-end integration test that calls `base.phasorpy.plot.plot_phasor` through `ExecutionService` and asserts `get_artifact(ref_id)` returns valid PNG bytes.

2. Relax reader selection / add fallback for mislabeled OME-TIFF inputs.
   - If the input file is declared `format: OME-TIFF` but the OME-TIFF reader fails, retry without an explicit reader so bioio can select an appropriate plugin (or explicitly retry Bio-Formats).
   - Alternatively, update the e2e test input format for FLUTE `.tif` files if they are not valid OME-TIFF.

3. Tighten provenance + allowlist coverage for this feature.
   - Add/extend tests to assert presence of input hashes and negative allowlist cases specific to phasorpy workflows.

