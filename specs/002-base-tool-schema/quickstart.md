# Quickstart: Adding a Base Toolkit Function

This guide explains how to add a new base image-processing function (typically backed by `scikit-image`) with reliable on-demand schemas.

## Prerequisites

- Tool pack runs in `env_id: bioimage-mcp-base`.
- The function MUST accept/produce artifact references (e.g., `BioImageRef`) rather than raw arrays in MCP payloads.
- The function MUST be describable via `meta.describe` so `describe_function(fn_id)` can return a complete parameter schema.

## 1. Implement the Operation

Create a new op module under the base tool pack ops directory.

**Proposed structure**:

```text
tools/base/
├── bioimage_mcp_base/
│   ├── ops/
│   │   └── gaussian.py
│   ├── descriptions.py
│   └── entrypoint.py
└── manifest.yaml
```

In `tools/base/bioimage_mcp_base/ops/gaussian.py`, implement a function with explicit keyword parameters, type hints, and defaults (so introspection is reliable).

## 2. Add Curated Parameter Descriptions

Add human-readable parameter descriptions in `tools/base/bioimage_mcp_base/descriptions.py`.

Example pattern:
- `GAUSSIAN_DESCRIPTIONS = {"sigma": "Standard deviation of the Gaussian kernel (pixels)."}`

These descriptions are used by `meta.describe` to avoid vague “See docs” outputs.

## 3. Wire Dispatch + `meta.describe`

Update `tools/base/bioimage_mcp_base/entrypoint.py` to:
- dispatch normal function execution requests by `fn_id`
- implement `meta.describe` by:
  - mapping `target_fn` → Python callable
  - calling `src/bioimage_mcp/runtimes/introspect.py::introspect_python_api(callable, descriptions)`
  - returning `{ok: true, result: {params_schema, tool_version, introspection_source}}`

## 4. Register the Function in the Manifest

Update `tools/base/manifest.yaml` to add a new `functions:` entry.

Guidelines:
- Keep `params_schema` minimal in the manifest (`type: object`, empty `properties`).
- Declare artifact I/O ports precisely (`inputs`/`outputs`).

Example sketch:

```yaml
- fn_id: base.gaussian
  tool_id: tools.base
  name: Gaussian filter
  description: Apply an N-D Gaussian filter.
  tags: [image, filter, preprocessing]
  inputs:
    - name: image
      artifact_type: BioImageRef
      required: true
  outputs:
    - name: output
      artifact_type: BioImageRef
      required: true
  params_schema:
    type: object
    properties: {}
```

## 5. Verify Schema Output

Once the server-side on-demand enrichment is wired, verify:
- `search_functions(query="gaussian")` lists `base.gaussian` with summary fields only.
- `describe_function("base.gaussian")` returns a complete schema:
  - required/optional params
  - types
  - defaults
  - curated descriptions
- repeated `describe_function("base.gaussian")` calls are served from the local JSON schema cache.

## 6. Add/Update Live Workflow Validation

If the function is used in the live workflow test:
- keep output paths run-isolated
- ensure the workflow operates on `datasets/FLUTE_FLIM_data_tif` inputs
- ensure the test either runs end-to-end (when envs exist) or skips with an actionable reason
