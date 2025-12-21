# Tutorial: Cellpose Segmentation

This tutorial guides you through running a cell segmentation workflow using the Cellpose integration.

## Prerequisites

*   Bioimage-MCP installed and configured.
*   Cellpose environment installed: `bioimage-mcp install --env bioimage-mcp-cellpose`.
*   An input microscopy image (TIFF/OME-TIFF).

## Step 1: Import the Image

First, we need to bring the image into the Bioimage-MCP system as an artifact.

```bash
bioimage-mcp artifacts import ./data/cells.tif --type BioImageRef --format OME-TIFF
```
*Note the returned `ref_id` (e.g., `artifact-123...`).*

## Step 2: Run Segmentation

You can run this via an MCP client or the Python API. Here is a Python example:

```python
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

INPUT_REF_ID = "artifact-123..." # Replace with your ID from Step 1

with ExecutionService(Config.from_file()) as svc:
    result = svc.run_workflow({
        "steps": [{
            "fn_id": "cellpose.segment",
            "params": {
                "model_type": "cyto3", 
                "diameter": 30.0
            },
            "inputs": {
                "image": {"ref_id": INPUT_REF_ID}
            }
        }]
    })

    labels_ref = result.outputs['labels']
    print(f"Segmentation complete. Labels Artifact ID: {labels_ref['ref_id']}")
```

## Step 3: Export Results

Export the resulting label image to a file for viewing (e.g., in Napari or Fiji).

```bash
bioimage-mcp artifacts export <labels_ref_id> ./results/seg_labels.tif
```
