---
status: resolved
trigger: "Investigate issue: export-fails-aicspylibczi"
created: 2026-01-25T13:58:11+01:00
updated: 2026-01-25T14:08:58+01:00
---

## Current Focus

hypothesis: base env spec + lockfile updates stabilize plugin discovery; removing bioio-sldy avoids numpy<2 conflict.
test: run bioio.plugins.get_plugins(use_cache=False) in current env; verify lockfile includes required deps and excludes bioio-sldy.
expecting: plugin discovery succeeds; lockfile includes aicspylibczi/pylibczirw/mrc and no bioio-sldy.
next_action: move to verification phase and provide user guidance for env recreation; optionally run export repro if possible.

## Symptoms

expected: Export should write the provided image artifact as an OME-TIFF at datasets/FLUTE_FLIM_data_tif/outputs/hMSC_control_loaded.ome.tif.
actual: Run fails with EXECUTION_FAILED and message `No module named '_aicspylibczi'`.
errors: Traceback shows `bioio.plugins.get_plugins()` loads entrypoints; importing `bioio_czi` triggers `from _aicspylibczi import BBox, TileInfo` and crashes. Paths seen: `tools/base/bioimage_mcp_base/ops/io.py:1169`, `tools/base/bioimage_mcp_base/utils.py`, `...site-packages/bioio/plugins.py:281`, `...site-packages/bioio_czi/...`.
reproduction: Call MCP run with `fn_id=base.io.bioimage.export`, `inputs.image=d53d0c66aa074c9787580acba3609f74`, `params.dest_path=datasets/FLUTE_FLIM_data_tif/outputs/hMSC_control_loaded.ome.tif`.
started: Unknown (assume current env on 2026-01-25).

## Eliminated

## Evidence

- timestamp: 2026-01-25T13:58:36+01:00
  checked: tools/base/bioimage_mcp_base/ops/io.py export path
  found: export() calls load_native_image(), which uses BioImage(path) without explicit reader selection; _export_ome_tiff uses OmeTiffWriter directly.
  implication: failure likely occurs during load_native_image (BioImage reader selection/plugin discovery), not during write.

- timestamp: 2026-01-25T13:58:36+01:00
  checked: tools/base/bioimage_mcp_base/utils.py load_native_image
  found: load_native_image -> load_native_image_fallback -> _load_image_internal -> BioImage(path) inside try; no guard around plugin loading.
  implication: BioImage initialization likely triggers bioio plugin discovery and imports all entrypoints, so missing CZI dependency can break TIFF export.

- timestamp: 2026-01-25T13:59:03+01:00
  checked: bioio.plugins.get_plugins and BioImage.determine_plugin in site-packages
  found: get_plugins iterates entry_points and calls ep.load().ReaderMetadata with no try/except; BioImage.determine_plugin calls get_plugins when reader is None.
  implication: any plugin import error (e.g., bioio_czi missing _aicspylibczi) aborts plugin discovery and fails BioImage initialization, impacting unrelated formats.

- timestamp: 2026-01-25T13:59:22+01:00
  checked: runtime call to bioio.plugins.get_plugins(use_cache=False)
  found: raises ModuleNotFoundError: No module named '_aicspylibczi'
  implication: reproduces failure directly; plugin discovery is the immediate crash point.

- timestamp: 2026-01-25T14:01:33+01:00
  checked: runtime call to bioio.plugins.get_plugins(use_cache=False) after lockfile update
  found: still raises ModuleNotFoundError: No module named '_aicspylibczi'
  implication: current environment still missing native module; lockfile update doesn't change active env.

- timestamp: 2026-01-25T14:01:54+01:00
  checked: aicspylibczi import and pip show in current env
  found: ModuleNotFoundError; package not installed
  implication: verification requires installing aicspylibczi into env or rebuilding from updated lockfile.

- timestamp: 2026-01-25T14:02:43+01:00
  checked: pip install aicspylibczi
  found: aicspylibczi 3.3.1 installed; pip warns bioio-czi requires pylibczirw
  implication: CZI stack still incomplete; plugin discovery may fail on missing pylibCZIrw.

- timestamp: 2026-01-25T14:02:55+01:00
  checked: runtime call to bioio.plugins.get_plugins(use_cache=False) after installing aicspylibczi
  found: raises ModuleNotFoundError: No module named 'pylibCZIrw'
  implication: additional dependency pylibCZIrw is required for bioio-czi.

- timestamp: 2026-01-25T14:03:42+01:00
  checked: runtime call to bioio.plugins.get_plugins(use_cache=False) after installing pylibczirw
  found: raises ModuleNotFoundError: No module named 'mrc'
  implication: another plugin dependency missing (likely mrcfile), so env-level fix is cascading.

- timestamp: 2026-01-25T14:04:42+01:00
  checked: user report on plugin requirements
  found: bioio-sldy==1.4.0 requires numpy<2, incompatible with python=3.13 / numpy>=2 in base env
  implication: base env plugin set must be audited and incompatible plugins removed or moved to separate env.

- timestamp: 2026-01-25T14:06:10+01:00
  checked: installed plugin metadata in current env
  found: bioio-czi 2.4.2 installed; bioio-dv 1.2.0 installed (requires mrc>=0.2.0); bioio-imageio and bioio-nd2 specify numpy>=1.21/1.16; bioio-sldy not installed in current env
  implication: base env spec includes plugins with external deps; we should make native deps explicit and remove incompatible bioio-sldy.

- timestamp: 2026-01-25T14:06:10+01:00
  checked: module 'mrc' availability
  found: mrc module importable in current env (mrc 0.3.1)
  implication: missing 'mrc' error is resolvable by ensuring mrc is installed when bioio-dv is present.

- timestamp: 2026-01-25T14:08:07+01:00
  checked: envs/bioimage-mcp-base.yaml current contents
  found: bioio-sldy excluded with note; aicspylibczi/pylibczirw pinned; mrc/nd2/resource_backed_dask_array added as conda deps; pip plugin versions pinned
  implication: env spec already incorporates audit outcomes; focus shifts to lockfile validation and guidance.

- timestamp: 2026-01-25T14:08:22+01:00
  checked: envs/bioimage-mcp-base.lock.yml for bioio-sldy and required deps
  found: bioio-sldy absent; aicspylibczi/pylibczirw/mrc present in lockfile
  implication: lockfile matches env spec for plugin audit changes.

- timestamp: 2026-01-25T14:08:37+01:00
  checked: bioio.plugins.get_plugins(use_cache=False) in current env
  found: succeeds ("plugins ok")
  implication: plugin discovery no longer fails when native deps are installed and incompatible plugins removed.

## Resolution

root_cause: "bioio plugin discovery eagerly loads all reader entrypoints; base env includes plugins with missing native deps (_aicspylibczi, pylibCZIrw, mrc) and at least one plugin (bioio-sldy) has incompatible numpy constraints for python=3.13, causing import failures and env conflicts."
fix: "Audit base env bioio plugins, remove incompatible ones (e.g., bioio-sldy) and add missing deps for retained plugins (aicspylibczi, pylibczirw; possibly mrcfile)."
verification: "bioio.plugins.get_plugins(use_cache=False) succeeds in current env; lockfile includes aicspylibczi/pylibczirw/mrc and excludes bioio-sldy."
files_changed:
  - envs/bioimage-mcp-base.yaml
  - envs/bioimage-mcp-base.lock.yml
