# CLI Reference

The `bioimage-mcp` command-line interface.

## Global Options
*   `--config <path>`: Path to config file (default: searches standard locations).
*   `--verbose`, `-v`: Enable verbose logging.

## Commands

### `serve`
Start the MCP server.
*   **Usage**: `bioimage-mcp serve`
*   **Transport**: Currently stdio.

### `install`
Install tool environments.
*   `--profile <name>`: Install a profile (e.g., `cpu`).
*   `--env <env_id>`: Install a specific environment by ID.
*   `--force`: Force re-installation.

### `doctor`
Run system readiness checks.
*   `--json`: Output results as JSON.

### `configure`
Create a starter configuration file.
*   **Usage**: `bioimage-mcp configure`

### `artifacts`
Manage the artifact store.

#### `import`
Import a file into the store.
*   `path`: Path to the source file.
*   `--type <type>`: Artifact type (e.g., `BioImageRef`).
*   `--format <format>`: File format (e.g., `OME-TIFF`).

#### `export`
Export an artifact to a file.
*   `ref_id`: The ID of the artifact to export.
*   `dest`: Destination path.
