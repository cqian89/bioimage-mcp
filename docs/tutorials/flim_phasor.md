# Tutorial: FLIM Phasor Analysis

This guide demonstrates how to perform Phasor analysis on Fluorescence Lifetime Imaging Microscopy (FLIM) data.

## Prerequisites

*   Bioimage-MCP installed.
*   Base environment installed (`bioimage-mcp install --profile cpu`).
*   A FLIM dataset in OME-TIFF format (must have a time/bin dimension).

## Data Preparation and Format

FLIM phasor analysis is highly sensitive to metadata and pixel dimensions. To ensure accurate results, the following guidelines should be followed:

*   **OME-TIFF Requirement**: The analysis tools specifically require the OME-TIFF format to correctly interpret time-resolved or binned FLIM data.
*   **Converting Proprietary Formats**: If your data is in a proprietary format (e.g., Zeiss `.czi`, Leica `.lif`, Nikon `.nd2`), you must convert it to OME-TIFF first using the `base.bioio.export` tool.
*   **Metadata Preservation**: Using `base.bioio.export` ensures that critical metadata (like voxel sizes and time-binning information) and all dimensions are preserved during the conversion process.

## Step 1: Compute Phasor Maps

The `base.phasorpy.phasor.phasor_from_signal` tool converts time-resolved data into phasor coordinates (real and imaginary) and an average intensity image.

Assuming you have an MCP client connected (or using Python API):

```python
# 1. Import FLIM data
# Assume 'flim_ref' is the artifact reference for your imported OME-TIFF

# 2. Run Phasor Transform
result = await mcp.call_tool(
    "base.phasorpy.phasor.phasor_from_signal",
    inputs={"signal": flim_ref},
    params={"harmonic": 1}
)

int_ref = result.outputs["output"]     # Mean intensity
g_ref = result.outputs["output_1"]     # Real (G) coordinates
s_ref = result.outputs["output_2"]     # Imaginary (S) coordinates
```

## Step 2: Denoise (Optional)

Phasor maps can be noisy. You can apply a filter to clean them up.

```python
denoised_g = await mcp.call_tool(
    "base.skimage.filters.gaussian",
    inputs={"image": g_ref},
    params={
        "sigma": 1.0
    }
)
```

## Step 3: Integrated Workflow

A common workflow is to use the intensity image derived from the FLIM data to perform segmentation.

```python
# 1. Get intensity image from Phasor tool
phasor_res = await mcp.call_tool(
    "base.phasorpy.phasor.phasor_from_signal", 
    inputs={"signal": flim_ref}
)
intensity_ref = phasor_res.outputs["output"]

# 2. Segment using Cellpose (requires cellpose env installed)
seg_res = await mcp.call_tool("cellpose.segment", inputs={"image": intensity_ref})
mask_ref = seg_res.outputs["labels"]
```
