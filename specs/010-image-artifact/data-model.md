# Data Model: 010-image-artifact (Standardized with bioio)

## Image Artifact Interoperability

Instead of a custom wrapper class, we use `bioio.BioImage` as the standardized interface within tool environments. The data model focuses on how artifact references are passed and how `bioio` interprets them.

### BioImage Interface (Standardized)
Tools are expected to use the following patterns for image interaction:

```python
from bioio import BioImage

# Loading an artifact from a local path
image = BioImage(artifact_path)

# Accessing the 5D TCZYX array (dask-backed)
data = image.data 

# Accessing physical metadata
pixel_sizes = image.physical_pixel_sizes  # (Z, Y, X) in microns
channels = image.channel_names            # List of strings
```

### Artifact Manifest Hints
The `manifest.yaml` for each tool pack defines its format preferences. This allows the server to perform preemptive conversions.

```yaml
# tools/cellpose/manifest.yaml
functions:
  - id: cellpose.segment
    interchange_format: OME-TIFF
    inputs:
      - name: image
        type: BioImageRef
```

## Serialization Format (Subprocess Boundary)

When an artifact is passed to a tool environment, it is serialized as a standard `ArtifactRef` dictionary. The tool-side runtime is responsible for resolving the local path.

```json
{
  "ref_id": "abc123",
  "uri": "file:///path/to/image.ome.tiff",
  "artifact_type": "BioImageRef",
  "format": "ome-tiff",
  "metadata": {
    "axes": "TCZYX",
    "shape": [10, 2, 50, 512, 512],
    "dtype": "uint16",
    "physical_pixel_sizes": [1.0, 0.5, 0.5]
  }
}
```

## Internal Conversion Registry
The MCP server maintains a lightweight registry of "Interchange Formats" for each environment to determine if an input needs conversion before the subprocess is launched.

1. **Source Format**: The format of the artifact in the store (e.g., `czi`).
2. **Target Format**: The `interchange_format` requested by the tool (e.g., `ome-tiff`).
3. **Action**: If Source != Target, the server uses a `base` tool (like `bioio.OmeTiffWriter`) to create a temporary or permanent interchange version.
