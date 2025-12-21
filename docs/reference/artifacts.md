# Artifact Reference

Bioimage-MCP uses a file-backed artifact system to handle large bioimage data efficiently. Instead of passing megabytes or gigabytes of data through the MCP JSON-RPC connection, tools pass **Artifact References**.

## Common Artifact Types

### `BioImageRef`
*   **Description**: Represents a general biological image (intensity data).
*   **Format**: Primarily OME-TIFF.
*   **Usage**: Input for most processing tools; output for transforms and filters.

### `LabelImageRef`
*   **Description**: Represents a segmentation result (integer labels).
*   **Format**: OME-TIFF (unsigned integer).
*   **Usage**: Output of segmentation tools (e.g., Cellpose). 0 usually represents background.

### `NativeOutputRef`
*   **Description**: Tool-specific raw output.
*   **Format**: Variable (e.g., `.npy` bundles, `.json` records).
*   **Usage**: storing model-specific data that doesn't fit into standard image formats.

### `LogRef`
*   **Description**: Execution logs.
*   **Format**: Text/Log file.
*   **Usage**: Debugging tool execution.

## Artifact Properties

An Artifact Reference typically contains:
*   `ref_id`: Unique identifier (UUID).
*   `uri`: Location of the file (file://...).
*   `artifact_type`: One of the types above.
*   `format`: File format (OME-TIFF, OME-Zarr, etc.).
*   `metadata`: Optional dictionary of extra info (shape, dtype, etc.).
