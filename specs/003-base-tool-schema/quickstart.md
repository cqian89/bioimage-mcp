# Quickstart: FLIM Phasor Analysis

This guide demonstrates how to perform FLIM phasor analysis using the `bioimage-mcp` tools.

## Prerequisites

- `bioimage-mcp` installed and running.
- A FLIM dataset in OME-TIFF format (must have time/bin dimension).

## 1. Compute Phasor Maps

Use `base.phasor_from_flim` to generate phasor coordinates (G, S) and an intensity image.

```python
# Example MCP tool call
result = await mcp.call_tool(
    "base.phasor_from_flim",
    inputs={"dataset": "path/to/flim_data.ome.tif"},
    params={"harmonic": 1}
)

g_ref = result.outputs["g_image"]
s_ref = result.outputs["s_image"]
int_ref = result.outputs["intensity_image"]
```

## 2. Denoise Phasor Maps (Optional)

Use `base.denoise_image` to reduce noise in the G and S maps.

```python
# Denoise G component using a median filter
denoised_g = await mcp.call_tool(
    "base.denoise_image",
    inputs={"image": g_ref},
    params={
        "method": "median",
        "radius": 3
    }
)
```

## 3. End-to-End Workflow

Combine phasor analysis with segmentation.

1.  **Phasor Transform**: Get Intensity Image from `base.phasor_from_flim`.
2.  **Segmentation**: Pass Intensity Image to `cellpose.segment` (or similar).

```python
# 1. Phasor
phasor_res = await mcp.call_tool("base.phasor_from_flim", inputs={"dataset": flim_ref})
intensity_ref = phasor_res.outputs["intensity_image"]

# 2. Segment (using existing cellpose tool)
seg_res = await mcp.call_tool("cellpose.segment", inputs={"image": intensity_ref})
mask_ref = seg_res.outputs["mask"]
```
