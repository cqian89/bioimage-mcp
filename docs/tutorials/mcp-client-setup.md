# MCP Client Setup Guide

This guide explains how to configure various AI coding assistants to act as clients for the Bioimage-MCP server.

## Overview

The Bioimage-MCP server runs locally and communicates via the Model Context Protocol (MCP) using standard input/output (stdio).

**Key Requirements:**
*   **Transport**: Stdio (Standard Input/Output)
*   **Command**: `python -m bioimage_mcp serve --stdio` or `bioimage-mcp serve --stdio`
*   **Environment**: Ensure you use the correct Python executable if running within a Conda/Micromamba environment.

Before configuring a client, verifying your installation is recommended:
```bash
bioimage-mcp doctor
```

---

## OpenCode Configuration

OpenCode uses `~/.config/opencode/opencode.json` (global) or `opencode.json` (project root).

Add the following to the `mcp` section of your configuration file:

### Standard Setup
```json
{
  "mcp": {
    "bioimage-mcp": {
      "type": "local",
      "command": ["python", "-m", "bioimage_mcp", "serve", "--stdio"],
      "enabled": true
    }
  }
}
```

### Conda/Micromamba Setup (Recommended)
If you installed Bioimage-MCP in a specific environment, use the absolute path to the Python executable:

```json
{
  "mcp": {
    "bioimage-mcp": {
      "type": "local",
      "command": [
        "/path/to/miniforge3/envs/bioimage-mcp-base/bin/python",
        "-m",
        "bioimage_mcp",
        "serve",
        "--stdio"
      ],
      "enabled": true
    }
  }
}
```

> **Note**: Replace `/path/to/miniforge3/...` with the actual path to your environment's python executable. You can find this by activating your environment and running `which python`.

After updating the config, reload OpenCode and verify the connection:
```bash
opencode mcp list
```

---

## Claude Desktop Configuration

For Claude Desktop, modify the configuration file located at:
*   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the server definition to `mcpServers`:

```json
{
  "mcpServers": {
    "bioimage-mcp": {
      "command": "python",
      "args": ["-m", "bioimage_mcp", "serve", "--stdio"]
    }
  }
}
```

As with OpenCode, if using a virtual environment, replace "python" with the full path to your python executable.

---

## Cursor Configuration

For Cursor, create or update `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "bioimage-mcp": {
      "command": "python",
      "args": ["-m", "bioimage_mcp", "serve", "--stdio"]
    }
  }
}
```

---

## Troubleshooting

*   **"Command not found"**: Ensure the `python` executable is in your PATH or use the absolute path.
*   **Connection Refused/Closed**: Run `bioimage-mcp doctor` to ensure all internal tool environments are healthy.
*   **Stdio issues**: The `--stdio` flag is mandatory. Ensure your client configuration includes this argument.
