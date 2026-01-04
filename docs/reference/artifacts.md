# Artifact Reference

Bioimage-MCP uses a file-backed artifact system to handle large bioimage data efficiently. Instead of passing megabytes or gigabytes of data through the MCP JSON-RPC connection, tools pass **Artifact References**.

## Common Artifact Types

### `BioImageRef`
*   **Description**: Represents a general biological image (intensity data).
*   **Format**: Primarily OME-TIFF or OME-Zarr.
*   **Usage**: Input for most processing tools; output for transforms and filters.
*   **Native Metadata**:
    *   `ndim`: Number of dimensions (e.g., 2, 3, 5).
    *   `dims`: Dimension order (e.g., `["Y", "X"]`, `["T", "C", "Z", "Y", "X"]`).
    *   `shape`: Size of each dimension.
    *   `dtype`: Data type (e.g., `uint8`, `float32`).
    *   `physical_pixel_sizes`: Physical scale (Z, Y, X) in micrometers.

### `LabelImageRef`
*   **Description**: Represents a segmentation result (integer labels).
*   **Format**: OME-TIFF or OME-Zarr (unsigned integer).
*   **Usage**: Output of segmentation tools (e.g., Cellpose). 0 usually represents background.
*   **Native Metadata**: Same as `BioImageRef`.

### `ScalarRef`
*   **Description**: Single-value outputs (e.g., thresholds, metrics).
*   **Format**: JSON.
*   **Usage**: Output of statistical or thresholding tools.
*   **Metadata**:
    *   `value`: The scalar value.
    *   `dtype`: Data type (e.g., `float`, `int`, `bool`).

### `TableRef`
*   **Description**: Tabular data (e.g., region properties, measurements).
*   **Format**: CSV.
*   **Usage**: Output of measurement tools.
*   **Metadata**:
    *   `columns`: List of column definitions with names and types.
    *   `row_count`: Number of rows in the table.
    *   `index_column`: (Optional) Name of the index column.

### `NativeOutputRef`
*   **Description**: Tool-specific raw output.
*   **Format**: Variable (e.g., `.npy` bundles, `.json` records).
*   **Usage**: Storing model-specific data that doesn't fit into standard image formats.

### `LogRef`
*   **Description**: Execution logs.
*   **Format**: Text/Log file.
*   **Usage**: Debugging tool execution.

## Dimension Metadata Explanation

The introduction of `ndim`, `dims`, and `shape` at the artifact reference level allows MCP agents to:
1.  **Validate compatibility** before executing a tool (e.g., ensuring a 3D tool isn't given a 2D image).
2.  **Plan operations** based on image size and dimensionality without downloading large data files.
3.  **Preserve intent**: If a tool reduces a 5D image to 2D (e.g., a max projection), the output artifact explicitly reports `ndim: 2` and `dims: ["Y", "X"]`.

## Artifact Properties

An Artifact Reference typically contains:
*   `ref_id`: Unique identifier (UUID).
*   `uri`: Location of the file (file://...).
*   `artifact_type`: One of the types above.
*   `format`: File format (OME-TIFF, OME-Zarr, etc.).
*   `metadata`: Optional dictionary of extra info (shape, dtype, etc.).
