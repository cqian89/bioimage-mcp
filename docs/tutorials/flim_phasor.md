# Tutorial: FLIM Phasor Analysis

This guide demonstrates how to perform Phasor analysis on Fluorescence Lifetime Imaging Microscopy (FLIM) data.

## Prerequisites

*   Bioimage-MCP installed.
*   Base environment installed (`bioimage-mcp install --profile cpu`).
*   A FLIM dataset in OME-TIFF format (must have a time/bin dimension).

## Step 1: Compute Phasor Maps

The `base.phasor_from_flim` tool converts time-resolved data into phasor coordinates (G and S) and an intensity image.

Assuming you have an MCP client connected (or using Python API):

```python
# 1. Import FLIM data
# Assume 'flim_ref' is the artifact reference for your imported OME-TIFF

# 2. Run Phasor Transform
result = await mcp.call_tool(
    "base.phasor_from_flim",
    inputs={"dataset": flim_ref},
    params={"harmonic": 1}
)

g_ref = result.outputs["g_image"]
s_ref = result.outputs["s_image"]
int_ref = result.outputs["intensity_image"]
```

## Step 2: Denoise (Optional)

Phasor maps can be noisy. You can apply a filter to clean them up.

```python
denoised_g = await mcp.call_tool(
    "base.denoise_image",
    inputs={"image": g_ref},
    params={
        "method": "median",
        "radius": 3
    }
)
```

## Step 3: Integrated Workflow

A common workflow is to use the intensity image derived from the FLIM data to perform segmentation.

```python
# 1. Get intensity image from Phasor tool
phasor_res = await mcp.call_tool("base.phasor_from_flim", inputs={"dataset": flim_ref})
intensity_ref = phasor_res.outputs["intensity_image"]

# 2. Segment using Cellpose (requires cellpose env installed)
seg_res = await mcp.call_tool("cellpose.segment", inputs={"image": intensity_ref})
mask_ref = seg_res.outputs["mask"]
```
