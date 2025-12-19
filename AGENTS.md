# bioimage-mcp Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-18

## Active Technologies
- Python 3.13 (core server; tool envs may differ) + MCP Python SDK (`mcp`), `pydantic` v2, `bioio` (+ `bioio-ome-tiff`) (001-cellpose-pipeline)
- Local filesystem artifact store + SQLite index (MVP) (001-cellpose-pipeline)

- Python 3.13 (core server; tool envs may pin differently) + Official MCP Python SDK (`mcp`), `pydantic` v2 (tool manifest validation), `bioio` (+ `bioio-ome-tiff`, optional `bioio-ome-zarr`), `sqlite` (via stdlib) (000-v0-bootstrap)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.13 (core server; tool envs may pin differently): Follow standard conventions

## Recent Changes
- 001-cellpose-pipeline: Added Python 3.13 (core server; tool envs may differ) + MCP Python SDK (`mcp`), `pydantic` v2, `bioio` (+ `bioio-ome-tiff`)

- 000-v0-bootstrap: Added Python 3.13 (core server; tool envs may pin differently) + Official MCP Python SDK (`mcp`), `pydantic` v2 (tool manifest validation), `bioio` (+ `bioio-ome-tiff`, optional `bioio-ome-zarr`), `sqlite` (via stdlib)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
