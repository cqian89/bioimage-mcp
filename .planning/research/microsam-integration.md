# Research: micro-sam API -> MCP run() Integration

This research focuses on exposing the `micro_sam` Python library API (organized by submodules) as MCP-callable functions, with IDs following:

`micro_sam.<submodule>.<callable>`

Primary reference: `https://computational-cell-analytics.github.io/micro-sam/micro_sam.html`

## What "include the API" means for MCP

For planning purposes, "include the API" is interpreted as:

- Every public, documented callable in `micro_sam` submodules is discoverable via the MCP registry (`list/search`) and has a schema (`describe`).
- `run()` can execute the callable in the isolated `bioimage-mcp-microsam` environment.
- Artifact boundary is preserved where feasible:
  - `numpy.ndarray` / image-like inputs become `BioImageRef` / `LabelImageRef`.
  - Stateful / heavy objects (predictors, decoders, embedding state) are passed via `ObjectRef`.
  - Outputs that are images become `BioImageRef` / `LabelImageRef`; complex/heterogeneous outputs become `NativeOutputRef`.

Some parts of the `micro_sam` API are inherently path-centric (training, evaluation CLIs, dataset utilities). These can be exposed with path parameters initially, with a follow-up plan to tighten artifact-first I/O where it matters.

## Submodules (per upstream docs)

Upstream `micro_sam` documents the following submodules:

- Headless/library-focused (Phase 22):
  - `micro_sam.automatic_segmentation`
  - `micro_sam.bioimageio`
  - `micro_sam.evaluation`
  - `micro_sam.inference`
  - `micro_sam.instance_segmentation`
  - `micro_sam.models`
  - `micro_sam.multi_dimensional_segmentation`
  - `micro_sam.object_classification`
  - `micro_sam.precompute_state`
  - `micro_sam.prompt_based_segmentation`
  - `micro_sam.prompt_generators`
  - `micro_sam.sample_data`
  - `micro_sam.training`
  - `micro_sam.util`
  - `micro_sam.visualization`
- Interactive (Phase 23):
  - `micro_sam.sam_annotator` (napari GUI)

Phase boundary requirement from the milestone rework:
- Phase 22: everything except `micro_sam.sam_annotator`.
- Phase 23: `micro_sam.sam_annotator`.

## Introspector (AST/docstring) feasibility

### API functions/classes

Feasibility is generally high because upstream publishes docstring-based API docs (pdoc) and functions have stable Python signatures.

Expected blockers:

- Non-JSON / non-artifact parameter types (e.g., `torch.device`, `pathlib.Path`, callables, napari layer types, model objects).
- Stateful class instances (`SamPredictor`, mask generators, decoders) and intermediate "state" objects.
- Large tensor outputs (embeddings) not naturally represented as `BioImageRef`.

Mitigations (preferred, matches existing adapters like `cellpose`):

- Expose constructors and key methods for important classes as MCP functions by mapping:
  - constructor -> returns `ObjectRef`
  - method -> first arg is `ObjectRef` instance
- Where necessary, provide thin wrappers with clean signatures + explicit docstrings so Introspector can emit stable JSON schemas.
- Use adapter-level parameter coercion:
  - `BioImageRef` -> `numpy.ndarray`
  - `LabelImageRef` -> `numpy.ndarray` (int labels)
  - `ObjectRef` -> resolved python object

### CLI commands vs API

Upstream documents CLI entrypoints such as:

- `micro_sam.info`
- `micro_sam.precompute_embeddings`
- `micro_sam.annotator_2d` / `micro_sam.annotator_3d` / `micro_sam.annotator_tracking` / `micro_sam.image_series_annotator`
- `micro_sam.train`
- `micro_sam.evaluate`
- `micro_sam.automatic_segmentation`

Schema generation difficulty:

- API callables: Introspector can read function signatures + docstrings directly.
- CLI entrypoints: often implemented via `argparse` / `click` / `typer` style wrappers. AST/docstring parsing yields little:
  - parameters may be encoded in decorator metadata, not signature
  - types/defaults are CLI-specific
  - many inputs are file paths, which does not align cleanly with artifact I/O

Recommendation:

- Prefer exposing the Python library API.
- If CLI parity is desired, implement MCP wrappers around the underlying library functions (not the CLI), so Introspector and artifact conversion remain robust.

## Planned adapter strategy

Implement a `MicrosamAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/microsam.py` that:

- Uses `Introspector` for schema extraction.
- Discovers public callables across `micro_sam.*` modules based on `dynamic_sources` in `tools/microsam/manifest.yaml`.
- Applies an allowlist/denylist for:
  - GUI-only callables in Phase 22 (deny `micro_sam.sam_annotator.*`)
  - private members (`_*`)
  - callables that cannot be represented safely (optional, documented)
- Implements execution-time coercion for `BioImageRef` and `ObjectRef` to satisfy artifact boundary.

## Wrapper hotspots (likely needed)

Examples of callables that will likely need wrappers for MCP friendliness:

- `micro_sam.instance_segmentation.AutomaticMaskGenerator` (+ `generate`)
- `micro_sam.instance_segmentation.InstanceSegmentationWithDecoder` (+ `generate`)
- `micro_sam.util.get_predictor` / embedding precompute helpers
- Multi-dimensional segmentation helpers that accept raw arrays + rich config objects

Wrappers should live in the tool pack (e.g., `tools/microsam/bioimage_mcp_microsam/api_wrappers.py`) but be registered under `micro_sam.<submodule>.<callable>` IDs via the adapter mapping.

## References

- Upstream API index: https://computational-cell-analytics.github.io/micro-sam/micro_sam.html
- Upstream GitHub: https://github.com/computational-cell-analytics/micro-sam
