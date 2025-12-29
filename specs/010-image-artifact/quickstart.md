# Quickstart: Using bioio for Image Artifacts

## Standard Loading Pattern (In Tool Functions)

Tools receive an `ArtifactRef` (as a dictionary). The tool function resolves the path and uses `bioio` for standardized loading.

```python
from bioio import BioImage

def my_tool_function(image_ref: dict):
    # 1. Resolve the artifact path (usually provided in the input dict by the runtime)
    path = image_ref["uri"].replace("file://", "")
    
    # 2. Use BioImage for standardized 5D TCZYX access
    img = BioImage(path)
    
    # 3. Access the data (lazy dask array)
    # This always returns a 5D array (T, C, Z, Y, X)
    data = img.data
    
    # 4. Perform processing (e.g., using scikit-image)
    # If the tool requires a numpy array, call compute() or use .data directly if it's small
    processed = my_processing_logic(data.compute())
    
    return processed
```

## Accessing Metadata

`bioio` provides normalized access to physical metadata, which is crucial for many biological analysis tasks.

```python
img = BioImage(path)

# Physical pixel sizes (Z, Y, X) - usually in microns
pz, py, px = img.physical_pixel_sizes

# Channel names (e.g., ["DAPI", "GFP", "Cy5"])
channels = img.channel_names

# Dimensions
print(f"Shape: {img.dims.shape}") # (T, C, Z, Y, X)
print(f"Order: {img.dims.order}") # Always TCZYX
```

## Efficient Slicing

For large datasets (e.g., OME-Zarr), `bioio` leverages `dask` to load only the required chunks.

```python
img = BioImage(path)

# Get only the first timepoint, first channel, middle Z-slice
# This does NOT load the whole image into RAM
slice_data = img.data[0, 0, 25, :, :]

# Compute the slice to get a numpy array
np_slice = slice_data.compute()
```

## Manifest Configuration

Tools should declare their preferred interchange format. This allows the MCP server to handle conversions (like CZI to OME-TIFF) before the tool is even called.

```yaml
# manifest.yaml
functions:
  - id: my_tool.process
    summary: Process an image
    interchange_format: OME-TIFF # Default; use OME-ZARR for large datasets
    inputs:
      - name: image
        type: BioImageRef
```
