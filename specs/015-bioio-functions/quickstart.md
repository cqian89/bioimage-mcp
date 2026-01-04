# Quickstart: Bioimage I/O Functions

**Feature**: 015-bioio-functions  
**Namespace**: `base.io.bioimage.*`

## Overview

This feature provides 6 curated functions for common bioimage I/O operations:

| Function | Purpose |
|----------|---------|
| `load` | Load image file into artifact system |
| `inspect` | Get metadata without loading pixels |
| `slice` | Extract subset of multi-dimensional image |
| `validate` | Check file readability and report issues |
| `get_supported_formats` | List available format readers |
| `export` | Save artifact to standard format |

## Usage Examples

### 1. Load an Image

```python
# MCP call via run_function
result = await run_function(
    fn_id="base.io.bioimage.load",
    inputs={},
    params={"path": "/data/experiment/sample.czi"}
)
# Returns: {"outputs": {"image": <BioImageRef>}}
```

### 2. Inspect Metadata

```python
# Get dimensions without loading pixels
result = await run_function(
    fn_id="base.io.bioimage.inspect",
    inputs={},
    params={"path": "/data/experiment/sample.czi"}
)
# Returns:
# {
#   "path": "/data/experiment/sample.czi",
#   "format": "CZI",
#   "shape": [1, 3, 50, 512, 512],
#   "dims": "TCZYX",
#   "dtype": "uint16",
#   "physical_pixel_sizes": {"X": 0.1, "Y": 0.1, "Z": 0.5},
#   "channel_names": ["DAPI", "GFP", "mCherry"]
# }
```

### 3. Slice a Multi-dimensional Image

```python
# Extract first channel, Z-slice 25
result = await run_function(
    fn_id="base.io.bioimage.slice",
    inputs={"image": loaded_image_ref},
    params={
        "slices": {
            "C": 0,
            "Z": 25
        }
    }
)
# Returns: {"outputs": {"output": <BioImageRef with shape [1, 1, 1, 512, 512]>}}
```

```python
# Extract timepoints 0-9
result = await run_function(
    fn_id="base.io.bioimage.slice",
    inputs={"image": loaded_image_ref},
    params={
        "slices": {
            "T": {"start": 0, "stop": 10}
        }
    }
)
```

### 4. Validate a File

```python
# Pre-flight check before pipeline
result = await run_function(
    fn_id="base.io.bioimage.validate",
    inputs={},
    params={"path": "/data/experiment/sample.czi"}
)
# Returns:
# {
#   "path": "/data/experiment/sample.czi",
#   "is_valid": true,
#   "reader_selected": "bioio-czi",
#   "format_detected": "CZI",
#   "issues": []
# }
```

### 5. Check Supported Formats

```python
result = await run_function(
    fn_id="base.io.bioimage.get_supported_formats",
    inputs={},
    params={}
)
# Returns:
# {
#   "formats": ["OME-TIFF", "OME-Zarr", "CZI", "LIF", "ND2", "PNG", "TIFF"]
# }
```

### 6. Export to Standard Format

```python
# Export to OME-TIFF
result = await run_function(
    fn_id="base.io.bioimage.export",
    inputs={"image": processed_image_ref},
    params={"format": "OME-TIFF"}
)
# Returns: {"outputs": {"output": <BioImageRef pointing to .ome.tiff file>}}

# Export 2D image to PNG
result = await run_function(
    fn_id="base.io.bioimage.export",
    inputs={"image": slice_2d_ref},
    params={"format": "PNG"}
)
```

## Complete Workflow Example

```python
# AI Agent workflow: Load → Inspect → Slice → Export

# 1. Check formats
formats = await run_function(fn_id="base.io.bioimage.get_supported_formats", inputs={}, params={})
print(f"Supported: {formats['formats']}")

# 2. Validate input
validation = await run_function(
    fn_id="base.io.bioimage.validate",
    inputs={},
    params={"path": "/data/sample.lif"}
)
if not validation["is_valid"]:
    raise ValueError(f"Invalid file: {validation['issues']}")

# 3. Load image
loaded = await run_function(
    fn_id="base.io.bioimage.load",
    inputs={},
    params={"path": "/data/sample.lif"}
)
image_ref = loaded["outputs"]["image"]

# 4. Inspect dimensions
meta = await run_function(
    fn_id="base.io.bioimage.inspect",
    inputs={},
    params={"path": "/data/sample.lif"}
)
print(f"Shape: {meta['shape']}, Dims: {meta['dims']}")

# 5. Slice central Z-plane
mid_z = meta["shape"][2] // 2
sliced = await run_function(
    fn_id="base.io.bioimage.slice",
    inputs={"image": image_ref},
    params={"slices": {"Z": mid_z}}
)
sliced_ref = sliced["outputs"]["output"]

# 6. Export as OME-TIFF
exported = await run_function(
    fn_id="base.io.bioimage.export",
    inputs={"image": sliced_ref},
    params={"format": "OME-TIFF"}
)
print(f"Saved to: {exported['outputs']['output']['uri']}")
```

## Error Handling

All functions return structured error responses:

```python
{
    "error": {
        "code": "PATH_NOT_ALLOWED",
        "message": "Path '/secret/data.tif' is not in allowed read paths",
        "details": {
            "allowed_paths": ["/data", "/home/user"]
        }
    }
}
```

Common error codes:
- `PATH_NOT_ALLOWED`: File outside configured allowlist
- `FILE_NOT_FOUND`: File does not exist
- `UNSUPPORTED_FORMAT`: No reader available for format
- `SLICE_OUT_OF_BOUNDS`: Slice indices exceed array dimensions
- `VALIDATION_FAILED`: File is corrupt or unreadable
