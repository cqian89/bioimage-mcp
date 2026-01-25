---
status: investigating
trigger: "Investigate why physical pixel sizes are lost in scipy.ndimage execution. Context: Input image (test_dims.tif) had physical pixel sizes: Y=1.0, X=1.0. Output image (from gaussian_filter) had Y=None, X=None. Phase: 06-infrastructure-n-d-foundation File: src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py"
created: 2026-01-25T20:59:09Z
updated: 2026-01-25T21:10:46Z
---

## Current Focus
hypothesis: Scipy ndimage outputs lose physical pixel sizes because the adapter writes OME-TIFF via OmeTiffWriter without passing physical_pixel_sizes into the writer, so the OME-XML in the output file is empty and artifact metadata extraction returns None.
test: Verify _save_image in scipy_ndimage uses OmeTiffWriter without physical_pixel_sizes and relies on metadata_override only for artifact metadata (not file metadata).
expecting: Output file written without physical_pixel_sizes in OME-XML; only metadata_override provides in-memory metadata, which is later replaced by extract_image_metadata reading the file.
next_action: Inspect scipy_ndimage _save_image and artifact import path to confirm metadata_override is overridden by extract_image_metadata.

## Symptoms
expected: Output image preserves physical pixel sizes (Y=1.0, X=1.0) from input test_dims.tif after gaussian_filter.
actual: Output image has physical pixel sizes Y=None, X=None after gaussian_filter.
errors: None reported.
reproduction: Run scipy.ndimage gaussian_filter via MCP on test_dims.tif and inspect output metadata.
started: Unknown (reported during Phase 06 UAT).

## Eliminated

## Evidence

- timestamp: 2026-01-25T21:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py
  found: Adapter passes through physical_pixel_sizes only if present in the input artifact metadata; output metadata otherwise omits them.
  implication: Loss likely occurs earlier when input artifact lacks physical_pixel_sizes metadata despite source file having it.

- timestamp: 2026-01-25T21:07:59Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py + artifacts/store.py
  found: _save_image writes via OmeTiffWriter without physical_pixel_sizes/channel_names, while import_file re-extracts metadata from the written file and only then applies metadata_override.
  implication: If the written OME-TIFF lacks pixel size metadata, extract_image_metadata yields None and output artifacts lose physical_pixel_sizes despite input having them.

- timestamp: 2026-01-25T21:10:26Z
  checked: tools/base/bioimage_mcp_base/entrypoint.py (handle_materialize)
  found: Materialize writes OME-TIFF via OmeTiffWriter without physical_pixel_sizes/channel_names.
  implication: Cross-env or mem:// materialization also strips physical pixel sizes, so downstream tools see missing metadata.

## Resolution
root_cause: "scipy_ndimage adapter writes output OME-TIFFs without passing physical_pixel_sizes to OmeTiffWriter; ArtifactStore then re-extracts metadata from the file (which has nearly empty OME-XML), so physical_pixel_sizes become None in output artifacts."
fix: ""
verification: ""
files_changed: []
