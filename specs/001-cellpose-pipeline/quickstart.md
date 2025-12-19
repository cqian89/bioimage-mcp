# Quickstart: v0.1 First Real Pipeline (Cellpose)

**Branch**: `001-cellpose-pipeline`  
**Date**: 2025-12-18  

This quickstart is a design-time guide for the v0.1 “first real pipeline” flow. It focuses on the happy path and the minimum commands and API calls needed to run a segmentation workflow and export artifacts.

## Prerequisites

- Python 3.13 environment for the core server/CLI.
- A configured artifact store root and filesystem allowlists that include:
  - Read access to your input dataset path
  - Write access to the artifact store root
  - Write access to your chosen export destination
- Tool registry manifests loaded from the configured tool manifest roots.

## 1) Start the server

Run the MCP server (exact transport/launch may vary):

- `python -m bioimage_mcp`

## 2) Discover the Cellpose segmentation function (paged)

1. List tools (paged):
   - Call `list_tools(limit=?, cursor=?)` until you find the segmentation tool pack.
2. Describe the tool:
   - Call `describe_tool(tool_id)` to list functions.
3. Describe the function (on-demand schema):
   - Call `describe_function(fn_id)` to fetch the I/O ports and `params_schema`.

Target function for v0.1:
- `fn_id`: `segmentation.cellpose_segment` (proposed; see `contracts/` for the canonical contract)

## 3) Import an input image as a `BioImageRef`

Import a local microscopy image file into the artifact store to obtain a structured artifact reference:

- Call: `artifacts.import_file(path, artifact_type="BioImageRef", format="OME-TIFF" | "TIFF" | ...)`
- Result: `ArtifactRef` payload with `ref_id` + `uri` (file URI) + metadata.

Notes:
- Import enforces filesystem read allowlists (unless the file already lives inside `artifact_store_root`).

## 4) Run a single-step workflow (Cellpose segmentation)

Submit a linear workflow spec with one step:

- `steps[0].fn_id`: `segmentation.cellpose_segment`
- `steps[0].inputs.image`: the input `BioImageRef` (by reference payload)
- `steps[0].params`: model + thresholds, etc.
- Optional: `run_opts.timeout_seconds`

Expected outputs:
- `labels`: `LabelImageRef` (default `OME-TIFF`)
- `log`: `LogRef`
- `workflow_record`: `NativeOutputRef` (format: `workflow-record-json`)

## 5) Check run status + retrieve outputs

Poll run status:

- Call: `execution.get_run_status(run_id)`
- Returns: `status`, `outputs` (artifact ref payloads), and `log_ref`.

Failure behavior:
- On failure, status is `failed` and a `log_ref` is still available (FR-003).

## 6) Export artifacts to a local destination

Export any artifact ref to a local path (enforcing filesystem write allowlists):

- Call: `artifacts.export(ref_id, dest_path)`
- Result: local file/directory written at `dest_path`.

## 7) Replay a prior run from a workflow record

Replay accepts a workflow record (`NativeOutputRef` with format `workflow-record-json`) and starts a new run:

- Call: `execution.replay_workflow(workflow_record_ref)`
- Result: new `run_id` and new output artifact refs of the same types.

