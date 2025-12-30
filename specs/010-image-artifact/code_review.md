## Code Review — 2025-12-30T00:39:32+00:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | Several `[X]` tasks point to files currently untracked; `conda-lock` regeneration (T005) not done for modified env; one unit test does not exercise project code. |
| Tests    | PASS | Selected tests run: 30 passed, 0 failed (contract+unit+integration); `bioio_ome_tiff` deprecation warnings only. |
| Coverage | LOW | No coverage metric run; gaps around extensionless artifact paths and cellpose non-dask inputs. |
| Architecture | PASS | Format canonicalization + bioio-based I/O aligns with `plan.md`; core conversion orchestrator/metadata enrichment still pending tasks (T020–T022). |
| Constitution | FAIL | Reproducibility gate violated: env YAML changed without updating corresponding `conda-lock` lockfile (T005). |

### Findings

- **CRITICAL**: `envs/bioimage-mcp-cellpose.yaml` changed but `envs/bioimage-mcp-cellpose.lock.yml` was not regenerated (T005). This violates Constitution IV (pinned envs) and the feature plan’s reproducibility gate.
- **HIGH**: `tools/cellpose/bioimage_mcp_cellpose/ops/segment.py` calls `bio_img.data.compute()` unconditionally. If `BioImage.data` is a NumPy array (common for OME-TIFF), this will raise `AttributeError`.
- **HIGH**: `BioImage(path)` is used without an explicit reader in multiple places (`tools/base/bioimage_mcp_base/io.py`, `tools/base/bioimage_mcp_base/utils.py`, cellpose segment). The artifact store is known to rename files to UUIDs without extensions; reader auto-detection may fail, triggering tifffile fallback and losing physical metadata/channel names.
- **HIGH**: Files referenced by completed tasks are currently **untracked** in git (`docs/developer/image_handling.md`, multiple new tests under `tests/contract/`, `tests/unit/`, `tests/integration/`). If not added to the PR, tasks are not actually delivered.
- **MEDIUM**: `load_image_fallback` exists in both `tools/base/bioimage_mcp_base/io.py` and `tools/base/bioimage_mcp_base/utils.py` (duplicated logic). Divergence risk.
- **MEDIUM**: `tests/integration/test_io_fallback_chain.py` test names/docstrings still describe an explicit `bioio-ome-tiff` → `bioformats` chain, but implementation now uses generic `BioImage` + tifffile fallback.
- **MEDIUM**: `tests/unit/base/test_bioimage_normalization.py` defines its own `normalize_to_5d()` helper in the test file, so it does not validate a project helper or production behavior.
- **LOW**: `docs/developer/image_handling.md` YAML examples use `id`/`type` keys that do not match the repository’s manifest schema (`name`/`artifact_type`).
- **LOW**: Untracked root artifacts (`test.tif`, `test_out.tif`, `test_out2.tif`) should be removed or gitignored to avoid accidental inclusion.

### Remediation / Suggestions

- Regenerate `envs/bioimage-mcp-cellpose.lock.yml` with `conda-lock` after changing `envs/bioimage-mcp-cellpose.yaml` (and do the same for any other modified env sources).
- Update cellpose loader to handle both dask-backed and NumPy-backed arrays (e.g., `data = bio_img.data.compute() if hasattr(bio_img.data, 'compute') else bio_img.data`).
- Make reader selection robust when extensions are missing:
  - If `image_ref['format'] == 'OME-TIFF'`, explicitly use `bioio_ome_tiff.Reader` when constructing `BioImage`.
  - Consider storing/retaining extensions in the artifact store, or routing all loads through a helper that uses the artifact `format` hint.
- Ensure all new tests/docs referenced by `[X]` tasks are added to git before PR review.
- Replace the self-contained normalization “unit test” with assertions against real codepaths (e.g., `base.wrapper.io.export_ome_tiff` always emitting 5D TCZYX).

### Evidence (commands run)

- `pytest -p no:cacheprovider -q tests/contract/test_base_env_bioio_contract.py tests/contract/test_cellpose_env_bioio_contract.py tests/contract/test_manifest_port_format_contract.py`
- `pytest -p no:cacheprovider -q tests/unit/base/test_io_fallback.py tests/unit/base/test_bioimage_loading.py tests/unit/api/test_metadata_extraction.py tests/unit/base/test_bioimage_lazy_loading.py tests/unit/base/test_bioimage_normalization.py`
- `pytest -p no:cacheprovider -q tests/integration/test_io_fallback_chain.py tests/integration/test_czi_import_workflow.py tests/integration/test_metadata_preservation_roundtrip.py`
