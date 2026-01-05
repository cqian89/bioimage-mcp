# Bioimage-MCP Documentation

Welcome to the documentation for **Bioimage-MCP**, an MCP server for bioimage analysis that orchestrates a customizable set of analysis tools in isolated environments.

## Overview

Bioimage-MCP bridges the gap between Large Language Models (LLMs) and complex bioimage analysis workflows. It provides:

*   **Stable API**: A discovery-first Model Context Protocol (MCP) interface.
*   **Isolation**: Tools run in dedicated Conda/Micromamba environments (e.g., Cellpose, scikit-image).
*   **Reproducibility**: All workflows are recorded and can be replayed.
*   **Artifact-based I/O**: Efficient handling of large image data via file-backed references (OME-TIFF).

## MCP API Surface

Bioimage-MCP exposes a stable 8-tool surface for AI interaction:

| Tool | Purpose |
|------|---------|
| `list` | Browse catalog nodes (environments, packages, modules, functions) |
| `describe` | Get full details for a function or catalog node |
| `search` | Find functions by query, keywords, or I/O types |
| `run` | Execute a function within a session |
| `status` | Poll the status of a background run |
| `artifact_info` | Get metadata and text previews for artifacts |
| `session_export` | Export session to a reproducible workflow artifact |
| `session_replay` | Replay a workflow from an exported record |

## Getting Started

*   [**Installation**](installation.md): Set up the server and environments.
*   [**Usage Guide**](usage.md): Learn the basics of the CLI and Python API.

## Tutorials

*   [**Cellpose Segmentation**](tutorials/cellpose_segmentation.md): Run deep learning-based cell segmentation.
*   [**FLIM Phasor Analysis**](tutorials/flim_phasor.md): Analyze Fluorescence Lifetime Imaging Microscopy data.

## Reference

*   [**Tool Reference**](reference/tools.md): Catalog of available tools and functions.

## Developer

*   [**Contributing**](developer/contributing.md): How to add new tools and contribute to the project.
*   [**Image Handling**](developer/image_handling.md): Standard practices for image I/O and metadata access.
