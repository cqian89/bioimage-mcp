# Quickstart: v0.0 Bootstrap

This quickstart demonstrates the v0.0 user stories in `specs/001-v0-bootstrap/spec.md`:
- install + readiness checks
- start server and discover tools on demand
- run two trivial built-ins end-to-end using artifact references

## 0) Configure filesystem roots

Bioimage-MCP is local-first and file-backed. Configure allowed filesystem roots before running tools.

Configuration is layered:
- global: `~/.bioimage-mcp/config.yaml`
- local override: `.bioimage-mcp/config.yaml` (per-project)

Minimal example:

```yaml
artifact_store_root: /home/you/.bioimage-mcp/artifacts
tool_manifest_roots:
  - /home/you/.bioimage-mcp/tools
fs_allowlist_read:
  - /home/you/data
fs_allowlist_write:
  - /home/you/.bioimage-mcp
  - /home/you/exports
fs_denylist:
  - /etc
  - /proc
```

## 1) Install and verify readiness

Intended CLI flow (see PRD/Constitution for constraints):

```bash
bioimage-mcp install --profile cpu
bioimage-mcp doctor
```

`doctor` must run 8 checks (Python, micromamba/conda, disk, permissions, base env, GPU, conda-lock, network) and produce actionable remediation steps for failures.

## 2) Start the server

Run the MCP server locally:

```bash
bioimage-mcp serve --stdio
```

(Transport details depend on the MCP host; v0.0 supports local-first usage.)

## 3) Discover tools and functions (summary-first)

Client pattern:
1) `list_tools(limit=20)` (paginated)
2) `search_functions(query="blur", tags=[...])` (paginated)
3) `describe_function(fn_id)` (full schema only here)

## 4) Run a trivial built-in function end-to-end

v0.0 includes two built-in functions:
- `builtin.gaussian_blur`
- `builtin.convert_to_ome_zarr`

**Format strategy note**: The v0.0 implementation produces OME-Zarr outputs. The project is pivoting to **OME-TIFF** as the default intermediate for maximum interoperability; v0.1 adds `builtin.convert_to_ome_tiff` and updates built-in/pipeline outputs to write OME-TIFF by default.

Inputs and outputs are always artifact references (file-backed), never embedded pixel payloads.

### Example: Convert an input image to OME-Zarr (v0.0)

1) Create or reference an input `BioImageRef` pointing at a readable file under `fs_allowlist_read`.
2) Call `run_workflow` with a 1-step workflow:
   - step `fn_id`: `builtin.convert_to_ome_zarr`
   - `inputs`: `{ "image": <BioImageRef> }`
   - `params`: `{}` (or conversion options)
3) Poll `get_run_status(run_id)` until `status == "succeeded"`.
4) Use `get_artifact(output_ref_id)` to fetch metadata (size, checksums) without downloading the pixels.

### Example: Gaussian blur

Run `builtin.gaussian_blur` with parameters (example):
- `sigma`: float or per-axis mapping (implementation-defined in v0.0)

The output is a new `BioImageRef` (OME-Zarr in v0.0; moving toward OME-TIFF as the default).

## 5) Export the output artifact

Export must be restricted to `fs_allowlist_write` roots.

Example flow:
1) Call `export_artifact(ref_id, dest_path)`.
2) Confirm the exported file/dir exists and matches the artifact’s recorded checksum.

## 6) Validate the quickstart (optional)

A lightweight validation script runs the quickstart flow against a temporary workspace.

```bash
scripts/validate_quickstart.sh
```

To validate the end-to-end execution path, provide a sample input image:

```bash
BIOIMAGE_MCP_SAMPLE_IMAGE=/absolute/path/to/image scripts/validate_quickstart.sh
```

## Notes (security + observability)

- Tool code runs with user privileges; subprocess isolation is for crash containment, not a security sandbox.
- Every run produces a log artifact (`LogRef`) and a run record with provenance.
