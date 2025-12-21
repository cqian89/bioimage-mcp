# Contributing

## Development Environment

1.  Clone the repository.
2.  Install development dependencies:
    ```bash
    pip install -e ".[dev]"
    ```
3.  Install pre-commit hooks (if applicable).

## Adding a New Tool

Tools are organized into "Tool Packs" inside the `tools/` directory.

### Structure
Each tool pack (e.g., `tools/mytool`) requires:
1.  **`manifest.yaml`**: Defines the tool ID, environment, and functions.
2.  **`bioimage_mcp_mytool/`**: Python package containing the implementation.

### Steps
1.  **Create the directory**: `tools/my_new_tool/`
2.  **Create Manifest**: Write `manifest.yaml` defining your functions.
3.  **Implement Functions**: Create the Python package and entrypoint. Functions should accept and return Artifact References.
4.  **Tests**: Add contract tests in `tests/contract/` and unit tests in `tests/unit/`.

## Architecture Principles

*   **Isolation**: Tools run in their own conda environments. Do not import heavy dependencies (torch, tensorflow) in the core server.
*   **Artifacts**: Always use `BioImageRef`, `LabelImageRef`, etc., for passing data. Never pass raw arrays in JSON.
*   **Discovery**: Keep the root tool list lightweight. Detailed schemas are fetched on demand.

## Running Tests

```bash
# Run all tests
pytest

# Run contract tests
pytest tests/contract/
```
